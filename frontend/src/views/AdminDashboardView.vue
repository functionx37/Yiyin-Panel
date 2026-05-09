<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Link, Setting, SwitchButton } from '@element-plus/icons-vue'
import type { DebugGroupItem, FeatureGroup, ToggleGroup, ToggleItem } from '../api'
import { api } from '../api'
import { clearAdminToken } from '../lib/auth'

interface FeatureSection {
  name: string
  items: ToggleItem[]
}

const router = useRouter()
const loading = ref(true)
const activeModule = ref<'toggle' | 'preview'>('toggle')
const activeGroupId = ref('')
const groups = ref<ToggleGroup[]>([])
const previewGroups = ref<DebugGroupItem[]>([])
const featureGroups = ref<FeatureGroup[]>([])
const savingKeys = ref<Record<string, boolean>>({})

const navItems = [
  { key: 'toggle', label: '功能开关', icon: Setting },
  { key: 'preview', label: '群聊预览', icon: Link },
] as const

const selectedGroup = computed(() => {
  return groups.value.find((group) => group.group_id === activeGroupId.value) ?? groups.value[0] ?? null
})

const featureSections = computed<FeatureSection[]>(() => {
  const current = selectedGroup.value
  if (!current) {
    return []
  }
  const matched = new Set<string>()
  const sections: FeatureSection[] = featureGroups.value
    .map((section) => {
      const items = current.toggles.filter((item) => section.members.includes(item.name))
      items.forEach((item) => matched.add(item.name))
      return items.length ? { name: section.name, items } : null
    })
    .filter((item): item is FeatureSection => Boolean(item))

  const rest = current.toggles.filter((item) => !matched.has(item.name))
  if (rest.length) {
    sections.push({ name: '其他功能', items: rest })
  }
  return sections
})

async function loadPage() {
  loading.value = true
  try {
    const [toggleResult, previewResult] = await Promise.all([
      api.admin.getToggles(),
      api.admin.getGroups(),
    ])
    groups.value = toggleResult.groups
    featureGroups.value = toggleResult.feature_groups
    previewGroups.value = previewResult.groups
    if (!activeGroupId.value && toggleResult.groups.length) {
      activeGroupId.value = toggleResult.groups[0].group_id
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '加载失败'
    ElMessage.error(message)
    if (message.includes('登录')) {
      clearAdminToken()
      await router.replace({ name: 'admin-login' })
    }
  } finally {
    loading.value = false
  }
}

async function toggleFeature(featureName: string, enabled: boolean) {
  const group = selectedGroup.value
  if (!group) {
    return
  }
  const row = group.toggles.find((item) => item.name === featureName)
  if (!row) {
    return
  }
  const previous = row.enabled
  const key = `${group.group_id}:${featureName}`
  row.enabled = enabled
  savingKeys.value[key] = true
  try {
    const updated = await api.admin.updateToggle(group.group_id, featureName, enabled)
    const index = groups.value.findIndex((item) => item.group_id === group.group_id)
    if (index >= 0) {
      groups.value[index] = updated
    }
    ElMessage.success(`${featureName} 已${enabled ? '启用' : '禁用'}`)
  } catch (error) {
    row.enabled = previous
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    savingKeys.value[key] = false
  }
}

function handleToggleChange(featureName: string, value: string | number | boolean) {
  void toggleFeature(featureName, Boolean(value))
}

async function logout() {
  clearAdminToken()
  await router.replace({ name: 'admin-login' })
}

async function openPreview(group: DebugGroupItem) {
  await router.push({
    name: 'group-site',
    params: { groupId: group.group_id },
    query: { token: group.token },
  })
}

onMounted(loadPage)
</script>

<template>
  <div class="dashboard-shell">
    <aside class="dashboard-aside">
      <div class="brand-box">
        <div class="brand-mark">YIYIN-PANEL</div>
        <h2>管理后台</h2>
      </div>
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-card"
        :class="{ active: activeModule === item.key }"
        @click="activeModule = item.key"
      >
        <component :is="item.icon" class="nav-icon" />
        <span>{{ item.label }}</span>
      </button>
      <button class="nav-card logout-card" @click="logout">
        <SwitchButton class="nav-icon" />
        <span>退出登录</span>
      </button>
    </aside>

    <main class="dashboard-main">
      <section v-if="activeModule === 'toggle'" class="content-card">
        <el-skeleton v-if="loading" :rows="8" animated />
        <el-empty v-else-if="!groups.length" description="暂无群聊" />
        <template v-else>
          <el-tabs v-model="activeGroupId" class="group-tabs">
            <el-tab-pane
              v-for="group in groups"
              :key="group.group_id"
              :label="group.group_name || group.group_id"
              :name="group.group_id"
            >
              <div class="group-header">
                <h3>{{ group.group_name || group.group_id }}</h3>
              </div>

              <section v-for="section in featureSections" :key="section.name" class="feature-section">
                <div class="section-kicker">{{ section.name }}</div>
                <div class="feature-table">
                  <div v-for="item in section.items" :key="item.name" class="feature-row">
                    <div class="feature-name">{{ item.name }}</div>
                    <div class="feature-actions">
                      <el-switch
                        :model-value="item.enabled"
                        :loading="savingKeys[`${group.group_id}:${item.name}`]"
                        @change="handleToggleChange(item.name, $event)"
                      />
                    </div>
                  </div>
                </div>
              </section>
            </el-tab-pane>
          </el-tabs>
        </template>
      </section>

      <section v-else class="content-card">
        <el-skeleton v-if="loading" :rows="8" animated />
        <el-empty v-else-if="!previewGroups.length" description="暂无群聊" />
        <div v-else class="preview-list">
          <button
            v-for="group in previewGroups"
            :key="group.group_id"
            type="button"
            class="preview-list__item"
            @click="openPreview(group)"
          >
            <span>{{ group.group_name || group.group_id }}</span>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>
