<template>
  <div class="profile-detail-page animate-fade-in">
    <div class="page-header">
      <div>
        <h1>资料详情</h1>
        <p>基本信息来自用户服务，头像 / 部门 / 岗位来自资料服务，前端合并展示</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
    </div>

    <!-- 两边数据都拿不到：错误页兜底，不让页面空白 -->
    <el-result
      v-if="!loading && !userOk && !profileOk"
      icon="error"
      title="暂时无法加载资料"
      sub-title="用户服务与资料服务均不可用，请稍后重试"
    >
      <template #extra>
        <el-button type="primary" @click="loadAll">重新加载</el-button>
      </template>
    </el-result>

    <template v-else>
      <!-- 降级提示：哪个服务挂了提示哪个 -->
      <el-alert
        v-if="!loading && (!userOk || profileDegraded || !profileOk)"
        class="degrade-alert"
        :closable="false"
        show-icon
        type="warning"
      >
        <template #title>
          <span v-if="!userOk">用户服务暂时不可用，基本信息显示不完整；</span>
          <span v-if="profileDegraded">资料服务调用用户服务失败，已降级展示；</span>
          <span v-if="!profileOk">资料服务暂时不可用，部门 / 岗位 / 头像缺失；</span>
          其余数据仍可正常查看。
        </template>
        <div v-for="(w, i) in profileWarnings" :key="i" class="degrade-detail">· {{ w }}</div>
      </el-alert>

      <el-skeleton :loading="loading" animated :rows="6">
        <div class="detail-grid">
          <!-- 合并展示卡片 -->
          <el-card class="merge-card">
            <div class="profile-hero">
              <el-avatar :size="88" :src="avatarUrl">
                {{ displayName?.charAt(0) || '?' }}
              </el-avatar>
              <div class="hero-meta">
                <h2>{{ displayName || '未知用户' }}</h2>
                <div class="hero-tags">
                  <el-tag v-if="department" type="primary">{{ department }}</el-tag>
                  <el-tag v-if="position" type="success" effect="plain">{{ position }}</el-tag>
                  <el-tag v-if="roleLabel" :type="roleTagType">{{ roleLabel }}</el-tag>
                  <el-tag v-if="profileDegraded" type="warning" size="small">资料服务已降级</el-tag>
                </div>
              </div>
            </div>

            <el-divider />

            <el-descriptions :column="2" border>
              <el-descriptions-item label="用户名">
                <span v-if="userOk">{{ basic.username }}</span>
                <span v-else class="missing">加载失败</span>
              </el-descriptions-item>
              <el-descriptions-item label="昵称">
                <span v-if="userOk">{{ basic.nickname || '-' }}</span>
                <span v-else class="missing">—</span>
              </el-descriptions-item>
              <el-descriptions-item label="邮箱">
                <span v-if="userOk">{{ basic.email || '-' }}</span>
                <span v-else class="missing">不可用</span>
              </el-descriptions-item>
              <el-descriptions-item label="手机号">
                <span v-if="userOk">{{ basic.phone || '-' }}</span>
                <span v-else class="missing">不可用</span>
              </el-descriptions-item>
              <el-descriptions-item label="部门（资料服务）">
                <span v-if="profileOk">{{ department || '-' }}</span>
                <span v-else class="missing">不可用</span>
              </el-descriptions-item>
              <el-descriptions-item label="岗位（资料服务）">
                <span v-if="profileOk">{{ position || '-' }}</span>
                <span v-else class="missing">不可用</span>
              </el-descriptions-item>
              <el-descriptions-item label="个人简介" :span="2">
                <span v-if="userOk">{{ basic.bio || '-' }}</span>
                <span v-else class="missing">不可用</span>
              </el-descriptions-item>
            </el-descriptions>
          </el-card>

          <!-- 编辑资料（资料服务字段，即使用户服务挂了也能改） -->
          <el-card class="edit-card" v-if="profileOk">
            <template #header>
              <span class="card-title">编辑资料（资料服务）</span>
            </template>
            <el-form
              ref="formRef"
              :model="form"
              :rules="rules"
              label-width="80px"
            >
              <el-form-item label="头像URL" prop="avatar">
                <el-input v-model="form.avatar" placeholder="头像图片地址" clearable />
              </el-form-item>
              <el-form-item label="部门" prop="department">
                <el-input v-model="form.department" placeholder="所属部门" clearable />
              </el-form-item>
              <el-form-item label="岗位" prop="position">
                <el-input v-model="form.position" placeholder="岗位名称" clearable />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="save">保存资料</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>
      </el-skeleton>

      <!-- 演示故障注入面板 -->
      <el-card class="demo-card">
        <template #header>
          <span class="card-title">降级演示（故障注入）</span>
        </template>
        <p class="demo-tip">
          点击按钮模拟服务故障，再点「刷新」观察页面如何降级：任一服务失败只提示不空白。
        </p>
        <el-space wrap>
          <el-button :type="faults.upstream ? 'danger' : 'default'" @click="toggleFault('upstream')">
            {{ faults.upstream ? '恢复' : '模拟' }}用户服务故障（资料服务视角）
          </el-button>
          <el-button :type="faults.self ? 'danger' : 'default'" @click="toggleFault('self')">
            {{ faults.self ? '恢复' : '模拟' }}资料服务故障
          </el-button>
          <el-button @click="clearFaults">清除全部故障</el-button>
        </el-space>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api, { setGlobalSilent } from '@/api'

const loading = ref(false)
const saving = ref(false)
const formRef = ref(null)

// 两个服务各自的数据与可用状态
const basic = ref({})          // user-service: /auth/me
const merged = ref(null)        // profile-service: /profiles/me（含 user/profile/degraded）
const userOk = ref(false)
const profileOk = ref(false)

const faults = reactive({ upstream: false, self: false })

const form = reactive({ avatar: '', department: '', position: '' })
const rules = {
  avatar: [{ max: 500, message: 'URL 最长 500 字符', trigger: 'blur' }],
  department: [{ max: 100, message: '部门最长 100 字符', trigger: 'blur' }],
  position: [{ max: 100, message: '岗位最长 100 字符', trigger: 'blur' }]
}

const profile = computed(() => merged.value?.profile || null)
const profileDegraded = computed(() => profileOk.value && !!merged.value?.degraded)
const profileWarnings = computed(() => merged.value?.warnings || [])

const avatarUrl = computed(() => profile.value?.avatar || basic.value?.avatar || '')
const displayName = computed(
  () => basic.value?.nickname
    || merged.value?.user?.nickname
    || basic.value?.username
    || merged.value?.user?.username
    || ''
)
const department = computed(() => profile.value?.department || '')
const position = computed(() => profile.value?.position || '')

const roleLabel = computed(() => {
  const role = basic.value?.role || merged.value?.user?.role
  return ({ admin: '管理员', manager: '管理者', user: '普通用户', guest: '访客' })[role] || ''
})
const roleTagType = computed(() => {
  const role = basic.value?.role || merged.value?.user?.role
  return ({ admin: 'danger', manager: 'warning', user: 'success', guest: 'info' })[role] || 'info'
})

// 并行请求两个服务，各自失败互不影响
async function loadAll() {
  loading.value = true
  const [userResult, profileResult] = await Promise.allSettled([
    api.auth.getCurrentUser(),
    api.profiles.getMerged()
  ])

  if (userResult.status === 'fulfilled') {
    basic.value = userResult.value.data || {}
    userOk.value = true
  } else {
    basic.value = {}
    userOk.value = false
  }

  if (profileResult.status === 'fulfilled') {
    merged.value = profileResult.value.data || null
    profileOk.value = true
    if (profile.value) {
      form.avatar = profile.value.avatar || ''
      form.department = profile.value.department || ''
      form.position = profile.value.position || ''
    }
  } else {
    merged.value = null
    profileOk.value = false
  }

  loading.value = false
}

async function save() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      await api.profiles.update({
        avatar: form.avatar || null,
        department: form.department || null,
        position: form.position || null
      })
      ElMessage.success('资料已保存')
      await loadAll()
    } catch (e) {
      // 全局拦截器已提示
    } finally {
      saving.value = false
    }
  })
}

async function toggleFault(kind) {
  const next = !faults[kind]
  try {
    if (kind === 'upstream') await api.profiles.setUpstreamFault(next)
    else await api.profiles.setSelfFault(next)
    faults[kind] = next
    ElMessage.info(next ? '故障已注入，点击「刷新」查看降级效果' : '故障已恢复')
  } catch (e) {
    ElMessage.error('故障开关操作失败（资料服务可能已宕机）')
  }
}

async function clearFaults() {
  try {
    await api.profiles.resetFaults()
    faults.upstream = false
    faults.self = false
    ElMessage.success('故障已清除')
  } catch (e) {
    ElMessage.error('清除失败')
  }
}

onMounted(() => {
  // 本页对每个请求都有内联降级 UI，关闭全局错误弹窗避免重复提示
  setGlobalSilent(true)
  loadAll()
})

onBeforeUnmount(() => {
  setGlobalSilent(false)
})
</script>

<style lang="scss" scoped>
.profile-detail-page {
  max-width: 1000px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;

  h1 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 4px;
  }

  p {
    color: var(--text-secondary);
    font-size: 14px;
  }
}

.degrade-alert {
  margin-bottom: 16px;
}

.degrade-detail {
  font-size: 12px;
  opacity: 0.8;
  margin-top: 2px;
}

.detail-grid {
  display: grid;
  gap: 20px;
}

.profile-hero {
  display: flex;
  align-items: center;
  gap: 20px;
}

.hero-meta {
  h2 {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 10px;
    color: var(--text-primary);
  }
}

.hero-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.missing {
  color: var(--el-color-warning);
  font-style: italic;
}

.demo-card {
  margin-top: 20px;
}

.demo-tip {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}
</style>
