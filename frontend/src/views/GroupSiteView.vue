<script setup lang="ts">
import { ChatLineSquare, Close, Download, PictureFilled } from '@element-plus/icons-vue'
import { computed, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FoodItem, GroupSummary, QuoteMemberGroup } from '../api'
import { api } from '../api'

type ActiveSection = 'foods' | 'quotes'

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
const selectedPreview = ref<{ title: string; imageUrl: string; downloadName: string } | null>(null)

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
}

function openFoodLightbox(food: FoodItem) {
  selectedPreview.value = {
    title: food.name,
    imageUrl: food.image_url,
    downloadName: food.name,
  }
}

function openQuoteLightbox(entry: QuoteMemberGroup['entries'][number], member: string) {
  selectedPreview.value = {
    title: member,
    imageUrl: entry.image_url,
    downloadName: `${member}-${entry.id}`,
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
                      v-for="entry in activeQuoteGroup.entries"
                      :key="entry.id"
                      class="quote-wall__item image-card quote-image-card"
                    >
                      <button
                        type="button"
                        class="quote-image-button"
                        @click="openQuoteLightbox(entry, activeQuoteGroup.member)"
                      >
                        <img :src="entry.image_url" :alt="activeQuoteGroup.member" loading="lazy" />
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
            <article v-for="food in foods" :key="food.id" class="food-wall__item">
              <button type="button" class="food-card" @click="openFoodLightbox(food)">
                <img :src="food.image_url" :alt="food.name" loading="lazy" />
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
    </template>
  </div>
</template>
