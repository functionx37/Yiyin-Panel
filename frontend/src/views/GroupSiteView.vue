<script setup lang="ts">
import { ChatLineSquare, Close, Download, PictureFilled, Edit } from '@element-plus/icons-vue'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElDialog, ElForm, ElFormItem, ElInput, ElSelect, ElButton } from 'element-plus'
import type { FoodItem, GroupSummary, QuoteMemberGroup } from '../api'
import { api } from '../api'

type ActiveSection = 'foods' | 'quotes'
type ImageWithDimensions = {
  image_width?: number | null
  image_height?: number | null
}

const route = useRoute()
const loading = ref(true)
const invalid = ref(false)
const invalidMessage = ref('链接已失效或无效。')
const summary = ref<GroupSummary | null>(null)
const rawQuoteGroups = ref<QuoteMemberGroup[]>([])
const rawFoods = ref<FoodItem[]>([])
const quoteGroups = ref<QuoteMemberGroup[]>([])
const foods = ref<FoodItem[]>([])
const activeSection = ref<ActiveSection>('foods')
const activeMember = ref('')
const memberSidebarOpen = ref(true)
const selectedPreview = ref<{ type: 'food' | 'quote'; id: string; title: string; imageUrl: string; downloadName: string; tags?: string[] } | null>(null)

const editFoodVisible = ref(false)
const editFoodLoading = ref(false)
const editFoodForm = ref({ name: '', tags: [] as string[] })

const tabs: Array<{ key: ActiveSection; label: string; icon: Component }> = [
  { key: 'foods', label: '食物图鉴', icon: PictureFilled },
  { key: 'quotes', label: '群友语录', icon: ChatLineSquare },
]

const groupId = computed(() => String(route.params.groupId ?? ''))
const token = computed(() => String(route.query.token ?? ''))
const activeQuoteGroup = computed(() => {
  return quoteGroups.value.find((group) => group.member === activeMember.value) ?? quoteGroups.value[0] ?? null
})

function shuffleArray<T>(items: T[]) {
  const copy = [...items]
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]]
  }
  return copy
}

function reshuffleFoods() {
  foods.value = shuffleArray(rawFoods.value)
}

function reshuffleQuotes() {
  quoteGroups.value = shuffleArray(rawQuoteGroups.value).map((group) => ({
    ...group,
    entries: shuffleArray(group.entries),
  }))

  if (!quoteGroups.value.length) {
    activeMember.value = ''
    return
  }

  if (!quoteGroups.value.some((group) => group.member === activeMember.value)) {
    activeMember.value = quoteGroups.value[0].member
  }
}

function reshuffleCurrentSection() {
  if (activeSection.value === 'foods') {
    reshuffleFoods()
    return
  }
  reshuffleQuotes()
}

async function loadPage() {
  if (!groupId.value || !token.value) {
    loading.value = false
    invalid.value = true
    invalidMessage.value = '缺少群号或 token，无法展示群聊数据。'
    return
  }

  loading.value = true
  invalid.value = false
  try {
    const [summaryResult, quotesResult, foodsResult] = await Promise.all([
      api.public.getSummary(groupId.value, token.value),
      api.public.getQuotes(groupId.value, token.value),
      api.public.getFoods(groupId.value, token.value),
    ])
    summary.value = summaryResult
    rawQuoteGroups.value = quotesResult.quote_groups
    rawFoods.value = foodsResult.items
    quoteGroups.value = []
    foods.value = []
    activeMember.value = quotesResult.quote_groups[0]?.member ?? ''
    reshuffleQuotes()
    reshuffleFoods()
  } catch (error) {
    invalid.value = true
    invalidMessage.value = error instanceof Error ? error.message : '页面加载失败。'
    ElMessage.error(invalidMessage.value)
  } finally {
    loading.value = false
  }
}

function setActiveSection(section: ActiveSection) {
  activeSection.value = section
}

function openMemberSidebar() {
  memberSidebarOpen.value = true
}

function closeMemberSidebar() {
  memberSidebarOpen.value = false
}

function selectMember(member: string) {
  activeMember.value = member
  closeMemberSidebar()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function openFoodLightbox(food: FoodItem) {
  selectedPreview.value = {
    type: 'food',
    id: food.id,
    title: food.name,
    imageUrl: food.image_url,
    downloadName: food.name,
    tags: food.tags,
  }
}

function openQuoteLightbox(entry: QuoteMemberGroup['entries'][number], member: string) {
  selectedPreview.value = {
    type: 'quote',
    id: entry.id,
    title: member,
    imageUrl: entry.image_url,
    downloadName: `${member}-${entry.id}`,
  }
}

function openEditFood() {
  if (selectedPreview.value?.type === 'food') {
    editFoodForm.value = {
      name: selectedPreview.value.title,
      tags: [...(selectedPreview.value.tags || [])],
    }
    editFoodVisible.value = true
  }
}

async function submitEditFood() {
  if (!selectedPreview.value || selectedPreview.value.type !== 'food') return
  
  editFoodLoading.value = true
  try {
    const updatedFood = await api.public.updateFood(groupId.value, token.value, selectedPreview.value.id, {
      name: editFoodForm.value.name,
      tags: editFoodForm.value.tags,
    })
    
    // update local state
    const index = rawFoods.value.findIndex(f => f.id === updatedFood.id)
    if (index !== -1) {
      rawFoods.value[index] = updatedFood
    }
    
    const displayIndex = foods.value.findIndex(f => f.id === updatedFood.id)
    if (displayIndex !== -1) {
      foods.value[displayIndex] = updatedFood
    }
    
    selectedPreview.value.title = updatedFood.name
    selectedPreview.value.downloadName = updatedFood.name
    selectedPreview.value.tags = updatedFood.tags
    
    ElMessage.success('更新成功')
    editFoodVisible.value = false
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '更新失败')
  } finally {
    editFoodLoading.value = false
  }
}

function closeLightbox() {
  selectedPreview.value = null
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeLightbox()
  }
}

function sanitizeFileName(name: string) {
  return name.replace(/[\\/:*?"<>|]/g, '_').trim()
}

async function downloadPreviewImage() {
  if (!selectedPreview.value) {
    return
  }

  try {
    const response = await fetch(selectedPreview.value.imageUrl)
    if (!response.ok) {
      throw new Error('下载图片失败。')
    }

    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = sanitizeFileName(selectedPreview.value.downloadName) || 'image'
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(objectUrl)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '下载图片失败。')
  }
}

function getSpicyTags(tags: string[]) {
  return tags.filter((tag) => tag.includes('辣'))
}

function getImageAspectStyle(item: ImageWithDimensions) {
  const width = item.image_width
  const height = item.image_height
  if (typeof width !== 'number' || typeof height !== 'number' || width <= 0 || height <= 0) {
    return undefined
  }
  return {
    aspectRatio: `${width} / ${height}`,
  }
}

function attachKeyboardListener() {
  window.addEventListener('keydown', handleKeydown)
}

function detachKeyboardListener() {
  window.removeEventListener('keydown', handleKeydown)
}

onMounted(() => {
  loadPage()
  attachKeyboardListener()
})

onActivated(() => {
  attachKeyboardListener()
  reshuffleCurrentSection()
})

onDeactivated(() => {
  detachKeyboardListener()
})

onBeforeUnmount(() => {
  detachKeyboardListener()
})

watch(() => [groupId.value, token.value], loadPage)
watch(activeSection, () => {
  if (activeSection.value !== 'quotes') {
    closeMemberSidebar()
  }
  reshuffleCurrentSection()
})
</script>

<template>
  <div class="group-page">
    <div v-if="loading" class="center-page">
      <el-card class="loading-card">
        <el-skeleton :rows="8" animated />
      </el-card>
    </div>

    <div v-else-if="invalid" class="center-page">
      <el-card class="loading-card expired-card">
        <div class="section-kicker">访问受限</div>
        <h1>链接已失效</h1>
        <p>{{ invalidMessage }}</p>
        <p class="muted-text">请在群聊内重新发送 <code>/web</code> 获取当天的新链接。</p>
      </el-card>
    </div>

    <template v-else>
      <section class="hero-card group-hero">
        <div>
          <div class="section-kicker group-hero__brand">YIYIN WEB</div>
          <h1>{{ summary?.group_name || groupId }}</h1>
        </div>
        <div class="metric-row">
          <div class="metric-card">
            <span>语录成员</span>
            <strong>{{ summary?.quote_member_count ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span>语录条数</span>
            <strong>{{ summary?.quote_count ?? 0 }}</strong>
          </div>
          <div class="metric-card">
            <span>公开食物</span>
            <strong>{{ summary?.food_count ?? 0 }}</strong>
          </div>
        </div>
      </section>

      <section class="content-card group-content-card">
        <div class="tab-switcher" role="tablist" aria-label="内容切换">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            class="tab-bookmark"
            :class="{ active: activeSection === tab.key }"
            :aria-selected="activeSection === tab.key"
            @click="setActiveSection(tab.key)"
          >
            <span class="tab-bookmark__icon">
              <component :is="tab.icon" />
            </span>
            <span>{{ tab.label }}</span>
          </button>
          <div class="tab-switcher__divider" aria-hidden="true" />
        </div>

        <div v-if="activeSection === 'quotes'">
            <div class="quotes-section">
              <div class="quotes-toolbar">
                <button type="button" class="quotes-sidebar-toggle" @click="openMemberSidebar">
                  <ChatLineSquare />
                  <span>群友</span>
                </button>
              </div>

              <div v-if="memberSidebarOpen" class="quotes-sidebar-backdrop" @click="closeMemberSidebar" />

              <div class="quotes-layout">
              <aside class="member-sidebar" :class="{ 'member-sidebar--open': memberSidebarOpen }">
                <div class="member-sidebar__header">
                  <div class="section-kicker">群友</div>
                  <button type="button" class="member-sidebar__close" @click="closeMemberSidebar">
                    <Close />
                  </button>
                </div>
                <button
                  v-for="member in quoteGroups"
                  :key="member.member"
                  class="member-button"
                  :class="{ active: member.member === activeMember }"
                  @click="selectMember(member.member)"
                >
                  <span>{{ member.member }}</span>
                </button>
              </aside>

              <div class="quotes-panel">
                <el-empty v-if="!activeQuoteGroup" description="该群暂无可展示语录" />
                <template v-else>
                  <div class="quote-wall">
                    <article
                      v-for="(entry, index) in activeQuoteGroup.entries"
                      :key="entry.id"
                      class="quote-wall__item image-card quote-image-card"
                    >
                      <button
                        type="button"
                        class="quote-image-button"
                        @click="openQuoteLightbox(entry, activeQuoteGroup.member)"
                      >
                        <img
                          :src="entry.image_url"
                          :alt="activeQuoteGroup.member"
                          :width="entry.image_width ?? undefined"
                          :height="entry.image_height ?? undefined"
                          :style="getImageAspectStyle(entry)"
                          :loading="index < 6 ? undefined : 'lazy'"
                          :fetchpriority="index < 6 ? 'high' : 'auto'"
                        />
                      </button>
                    </article>
                  </div>
                </template>
              </div>
            </div>
            </div>
        </div>

        <div v-else>
          <el-empty v-if="!foods.length" description="该群暂无公开食物数据" />
          <div v-else class="food-wall">
            <article v-for="(food, index) in foods" :key="food.id" class="food-wall__item">
              <button type="button" class="food-card" @click="openFoodLightbox(food)">
                <img
                  :src="food.image_url"
                  :alt="food.name"
                  :width="food.image_width ?? undefined"
                  :height="food.image_height ?? undefined"
                  :style="getImageAspectStyle(food)"
                  :loading="index < 6 ? undefined : 'lazy'"
                  :fetchpriority="index < 6 ? 'high' : 'auto'"
                />
                <div class="image-card__footer">
                  <strong>{{ food.name }}</strong>
                  <div v-if="getSpicyTags(food.tags).length" class="tag-row">
                    <span v-for="tag in getSpicyTags(food.tags)" :key="tag" class="spicy-tag">{{ tag }}</span>
                  </div>
                </div>
              </button>
            </article>
          </div>
        </div>
      </section>

      <div v-if="selectedPreview" class="lightbox-overlay" @click.self="closeLightbox">
        <div class="lightbox-card" role="dialog" aria-modal="true" :aria-label="selectedPreview.title">
          <div class="lightbox-toolbar">
            <strong>{{ selectedPreview.title }}</strong>
            <div class="lightbox-actions">
              <button v-if="selectedPreview.type === 'food'" type="button" class="lightbox-icon-button" @click="openEditFood" title="编辑信息">
                <Edit />
              </button>
              <button type="button" class="lightbox-icon-button" @click="downloadPreviewImage">
                <Download />
              </button>
              <button type="button" class="lightbox-icon-button" @click="closeLightbox">
                <Close />
              </button>
            </div>
          </div>
          <div class="lightbox-media">
            <img :src="selectedPreview.imageUrl" :alt="selectedPreview.title" />
          </div>
        </div>
      </div>

      <el-dialog v-model="editFoodVisible" title="编辑食物信息" width="400px" append-to-body>
        <el-form label-width="80px" @submit.prevent>
          <el-form-item label="名称">
            <el-input v-model="editFoodForm.name" />
          </el-form-item>
          <el-form-item label="标签">
            <el-select v-model="editFoodForm.tags" multiple filterable allow-create default-first-option placeholder="请选择或输入标签">
            </el-select>
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="editFoodVisible = false">取消</el-button>
            <el-button type="primary" @click="submitEditFood" :loading="editFoodLoading">保存</el-button>
          </span>
        </template>
      </el-dialog>
    </template>
  </div>
</template>
