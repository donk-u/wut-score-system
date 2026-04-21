<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'
import { 
  User, Checked, DataLine, Setting, 
  Upload, Download, Delete, Search, Refresh, Expand, Bell, ChatDotRound, Promotion
} from '@element-plus/icons-vue'
import request from '../utils/request'

// ==========================================
// 1. 导航与全局状态
// ==========================================
const activeMenu = ref('1') 
const handleMenuSelect = async (index) => {
  activeMenu.value = index
  if (index === '1') await fetchStats()
  if (index === '2') await fetchStudents()
  if (index === '3') await fetchApplications()
  if (index === '4') await fetchRules()
}

// ==========================================
// 2. 🤖 AI 教务管家侧边舱
// ==========================================
const aiDrawerVisible = ref(false)
const chatInput = ref('')
const chatLoading = ref(false)
const chatContainer = ref(null)
const chatHistory = ref([
  { role: 'ai', content: '老师您好！我是大模型教务管家。我已经读取了当前的审核队列数据，您可以让我帮您分析进度，或者揪出异常加分的申请。' }
])

const sendChatMessage = async () => {
  if (!chatInput.value.trim()) return
  const question = chatInput.value
  chatHistory.value.push({ role: 'user', content: question })
  chatInput.value = ''
  
  await nextTick()
  if(chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight

  chatLoading.value = true
  try {
    const res = await request.post('/teacher/chat', { question: question })
    chatHistory.value.push({ role: 'ai', content: res.reply })
  } catch (e) {
    chatHistory.value.push({ role: 'ai', content: '糟糕，连接大模型时发生网络波动...' })
  } finally {
    chatLoading.value = false
    await nextTick()
    if(chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// ==========================================
// 3. 📊 数据大屏模块
// ==========================================
const stats = reactive({ summary: { total_students: 0, active_rate: 0, total_score: 0 }, pie_data: [] })
const chartRef = ref(null)
let myChart = null

const initChart = (data) => {
  if (!chartRef.value) return
  if (!myChart) myChart = echarts.init(chartRef.value)
  myChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '5%', left: 'center' },
    series: [{
      name: '申请状态', type: 'pie', radius: ['40%', '70%'],
      avoidLabelOverlap: false, itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
      label: { show: false, position: 'center' }, emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
      data: data
    }]
  })
}

const fetchStats = async () => {
  try {
    const res = await request.get('/teacher/statistics')
    Object.assign(stats, res)
    await nextTick(); initChart(res.pie_data)
  } catch (error) {}
}

// ==========================================
// 4. 📂 学生档案管理模块
// ==========================================
const studentData = ref([]); const studentLoading = ref(false); const uploadLoading = ref(false)

const fetchStudents = async () => {
  studentLoading.value = true
  try { studentData.value = await request.get('/teacher/students') } catch (error) {} finally { studentLoading.value = false }
}

const handleFileUpload = async (uploadFile) => {
  if (!uploadFile.raw) return
  const formData = new FormData(); formData.append('file', uploadFile.raw)
  uploadLoading.value = true
  try {
    const res = await request.post('/teacher/import/students', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success(`导入成功！新增 ${res.success_count} 人，跳过重复 ${res.skip_count} 人`)
    fetchStudents()
  } catch (error) {} finally { uploadLoading.value = false }
}
const handleExport = () => window.open('http://127.0.0.1:8000/api/v1/teacher/export/students', '_blank')
const handleClearAll = () => {
  ElMessageBox.confirm('此操作将永久清空所有档案，确定吗？', '严正警告', { confirmButtonText: '确定清空', cancelButtonText: '取消', type: 'error' })
  .then(async () => { await request.delete('/teacher/students/clear'); ElMessage.success('数据库已归零'); fetchStudents() }).catch(() => {})
}

// ==========================================
// 5. ⚖️ 证明审核模块
// ==========================================
const reviewData = ref([]); const reviewLoading = ref(false)

const fetchApplications = async () => {
  reviewLoading.value = true
  try { reviewData.value = await request.get('/teacher/applications') } catch (error) {} finally { reviewLoading.value = false }
}

const handleReview = async (id, status) => {
  const type = status === '已通过' ? 'success' : 'warning'
  ElMessageBox.confirm(`确定要标记该申请为【${status}】吗？`, '审核决策', { confirmButtonText: '确定', cancelButtonText: '取消', type: type })
  .then(async () => {
    await request.put(`/teacher/applications/${id}/review`, { status })
    ElMessage.success(`已标记为 ${status}`); fetchApplications()
  }).catch(() => {})
}

// ==========================================
// 6. ⚙️ 核心参数设置 (动态规则引擎)
// ==========================================
const ruleData = ref([])
const ruleLoading = ref(false)
const ruleDialogVisible = ref(false)
const newRule = reactive({ category: 'A1', level: '国家级', grade: '一等奖', position: 1, score: 5.0 })

const fetchRules = async () => {
  ruleLoading.value = true
  try { ruleData.value = await request.get('/teacher/rules') } catch (e) {} finally { ruleLoading.value = false }
}

const submitRule = async () => {
  try {
    await request.post('/teacher/rules', newRule)
    ElMessage.success('规则配置已全局生效！AI 将采用新标准算分。')
    ruleDialogVisible.value = false
    fetchRules()
  } catch (e) {}
}

const handleDeleteRule = async (id) => {
  ElMessageBox.confirm('删除此规则后，AI 将无法匹配对应加分，确定吗？', '删除确认', { type: 'warning' })
  .then(async () => {
    await request.delete(`/teacher/rules/${id}`)
    ElMessage.success('规则已卸载')
    fetchRules()
  }).catch(() => {})
}

// --- 初始化加载大屏 ---
onMounted(() => handleMenuSelect('1'))
</script>

<template>
  <div class="flex h-screen bg-[#f4f7f9] w-full overflow-hidden font-sans">
    
    <div class="w-64 bg-[#304156] text-white flex flex-col shadow-2xl z-20">
      <div class="h-16 flex items-center justify-center font-bold text-lg tracking-tighter border-b border-gray-700/50 bg-[#2b3a4d]">
        <img src="/logo.jpg" alt="Logo" class="w-8 h-8 mr-3 rounded-full border border-gray-500 shadow-sm" />
        <span>经管教务管理端</span>
      </div>
      <el-menu active-text-color="#409eff" background-color="#304156" class="border-none w-full flex-1" :default-active="activeMenu" text-color="#bfcbd9" @select="handleMenuSelect">
        <el-menu-item index="1"><el-icon><DataLine /></el-icon><span>全院数据大屏</span></el-menu-item>
        <el-menu-item index="2"><el-icon><User /></el-icon><span>学生档案管理</span></el-menu-item>
        <el-menu-item index="3"><el-icon><Checked /></el-icon><span>加分证明审核</span></el-menu-item>
        <el-menu-item index="4"><el-icon><Setting /></el-icon><span>核心参数设置</span></el-menu-item>
      </el-menu>
      <div class="p-4 bg-[#263445] text-xs text-gray-500 text-center italic">Backend v3.5 | Security Mode</div>
    </div>

    <div class="flex-1 flex flex-col overflow-hidden relative">
      
      <header class="h-14 bg-white shadow-sm flex items-center justify-between px-6 z-10">
        <div class="flex items-center text-gray-500">
          <el-icon class="mr-4 text-xl cursor-pointer hover:text-blue-500"><Expand /></el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>管理中心</el-breadcrumb-item>
            <el-breadcrumb-item v-if="activeMenu === '1'">全院大屏</el-breadcrumb-item>
            <el-breadcrumb-item v-if="activeMenu === '2'">学生管理</el-breadcrumb-item>
            <el-breadcrumb-item v-if="activeMenu === '3'">证明审核</el-breadcrumb-item>
            <el-breadcrumb-item v-if="activeMenu === '4'">核心引擎配置</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="flex items-center space-x-4">
          <el-button type="primary" round icon="ChatDotRound" color="#6366f1" @click="aiDrawerVisible = true" class="shadow-md animate-pulse">
            唤醒 AI 智能管家
          </el-button>
          <el-badge is-dot class="cursor-pointer mx-2"><el-icon class="text-xl text-gray-400"><Bell /></el-icon></el-badge>
          <div class="flex items-center ml-2">
            <span class="mr-2 text-sm font-semibold text-gray-700">超级管理员</span>
            <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
          </div>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-8 bg-[#f8fafc]">
        <transition name="fade-slide" mode="out-in">
          
          <div v-if="activeMenu === '1'" key="menu-1" class="max-w-7xl mx-auto space-y-8">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div class="bg-gradient-to-br from-blue-500 to-blue-600 p-8 rounded-3xl text-white shadow-lg">
                <div class="opacity-80 text-sm">全院档案总数</div><div class="text-5xl font-black mt-2">{{ stats.summary.total_students }} <small class="text-lg">人</small></div>
              </div>
              <div class="bg-gradient-to-br from-indigo-500 to-purple-600 p-8 rounded-3xl text-white shadow-lg">
                <div class="opacity-80 text-sm">系统激活率</div><div class="text-5xl font-black mt-2">{{ stats.summary.active_rate }}%</div>
              </div>
              <div class="bg-gradient-to-br from-emerald-500 to-teal-600 p-8 rounded-3xl text-white shadow-lg">
                <div class="opacity-80 text-sm">已核准总分值</div><div class="text-5xl font-black mt-2">+ {{ stats.summary.total_score }}</div>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div class="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
                <h3 class="font-bold text-gray-700 mb-6 flex justify-between items-center">实时申请分布图 <el-button type="primary" size="small" plain icon="Download" @click="handleExport">导出报表</el-button></h3>
                <div ref="chartRef" style="height: 400px; width: 100%;"></div>
              </div>
              <div class="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 flex flex-col justify-center">
                <h3 class="font-bold text-gray-700 mb-4">管理决策建议</h3>
                <div class="space-y-4">
                  <el-alert title="数据流转正常" type="success" description="教务数据中心正在实时监听各专业综测动态。" show-icon :closable="false" />
                  <p class="text-gray-500 text-sm leading-relaxed p-4 bg-gray-50 rounded-xl">建议您点击右上角的「唤醒 AI 智能管家」，让系统大模型自动为您筛查待审核队列中是否存在重复提交、或者分值异常偏高的竞赛记录。</p>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="activeMenu === '2'" key="menu-2" class="max-w-7xl mx-auto space-y-6">
            <div class="bg-white rounded-xl border border-gray-200 p-6 flex justify-between items-center shadow-sm">
              <div class="flex items-center gap-3">
                <el-upload action="" :auto-upload="false" :show-file-list="false" :on-change="handleFileUpload" accept=".xlsx, .xls"><el-button type="primary" icon="Upload" :loading="uploadLoading">一键导入名单</el-button></el-upload>
                <el-button type="success" icon="Download" plain @click="handleExport">导出全量档案</el-button>
                <el-button type="danger" icon="Delete" plain @click="handleClearAll">清空数据库</el-button>
              </div>
              <div class="flex items-center gap-3">
                <el-input placeholder="搜索学号、姓名..." prefix-icon="Search" style="width: 250px" clearable /><el-button icon="Refresh" circle @click="fetchStudents" :loading="studentLoading" />
              </div>
            </div>
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <el-table v-loading="studentLoading" :data="studentData" border stripe style="width: 100%" :header-cell-style="{ background: '#f8f9fb', color: '#444', fontWeight: '800' }">
                <el-table-column type="index" label="序号" width="70" align="center" />
                <el-table-column prop="student_id" label="学号" width="160" align="center" sortable />
                <el-table-column prop="name" label="姓名" width="130" align="center"><template #default="scope"><span class="font-bold text-gray-800">{{ scope.row.name }}</span></template></el-table-column>
                <el-table-column prop="major" label="专业" width="180" />
                <el-table-column prop="email" label="验证邮箱" min-width="200"><template #default="scope"><span class="text-gray-400 italic text-sm">{{ scope.row.email || '未注册' }}</span></template></el-table-column>
                <el-table-column label="状态" width="120" align="center"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'warning'" effect="dark" round>{{ scope.row.is_active ? '已激活' : '待注册' }}</el-tag></template></el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else-if="activeMenu === '3'" key="menu-3" class="max-w-7xl mx-auto space-y-6">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div class="p-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                <div class="font-bold text-gray-700 flex items-center"><el-icon class="mr-2 text-blue-500"><Checked /></el-icon> AI 智能初审待办队列</div>
                <el-button icon="Refresh" circle @click="fetchApplications" :loading="reviewLoading" />
              </div>
              <el-table v-loading="reviewLoading" :data="reviewData" border stripe style="width: 100%" :header-cell-style="{ background: '#f8f9fb', color: '#444', fontWeight: '800' }">
                <el-table-column prop="student_name" label="申请人" width="100" align="center" />
                <el-table-column prop="award_name" label="竞赛/奖项名称" min-width="220"><template #default="scope"><span class="text-blue-600 font-semibold">{{ scope.row.award_name }}</span></template></el-table-column>
                <el-table-column prop="award_level" label="级别" width="140" align="center"><template #default="scope"><el-tag type="warning" effect="dark" round size="small">{{ scope.row.award_level }}</el-tag></template></el-table-column>
                <el-table-column label="AI 建议加分" width="120" align="center"><template #default="scope"><span class="text-lg font-black text-green-500">+ {{ scope.row.suggested_score }}</span></template></el-table-column>
                <el-table-column label="状态" width="110" align="center"><template #default="scope"><el-tag :type="scope.row.status === '待审核' ? 'info' : (scope.row.status === '已通过' ? 'success' : 'danger')">{{ scope.row.status }}</el-tag></template></el-table-column>
                <el-table-column label="教务操作" width="180" align="center" fixed="right">
                  <template #default="scope">
                    <template v-if="scope.row.status === '待审核'">
                      <el-button size="small" type="success" plain @click="handleReview(scope.row.id, '已通过')">通过</el-button>
                      <el-button size="small" type="danger" plain @click="handleReview(scope.row.id, '已驳回')">驳回</el-button>
                    </template>
                    <span v-else class="text-gray-400 text-sm italic">审核已归档</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <div v-else-if="activeMenu === '4'" key="menu-4" class="max-w-7xl mx-auto space-y-6">
            <div class="bg-gradient-to-r from-gray-800 to-gray-700 p-8 rounded-2xl text-white shadow-xl flex justify-between items-center">
              <div>
                <h2 class="text-2xl font-black mb-2 tracking-wide flex items-center"><el-icon class="mr-2"><Setting /></el-icon> 加分规则动态引擎 (Rule Engine)</h2>
                <p class="text-gray-300 text-sm">在此处配置的 A1/A2/B 类赛事位次加分逻辑，将直接接管 AI 的自动算分系统。</p>
              </div>
              <el-button type="primary" size="large" round color="#6366f1" class="shadow-lg border-none" @click="ruleDialogVisible = true">
                + 新增赛事加分规则
              </el-button>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden p-6">
              <el-table v-loading="ruleLoading" :data="ruleData" border stripe style="width: 100%" :header-cell-style="{ background: '#f8f9fb', color: '#444', fontWeight: '800' }">
                <el-table-column prop="category" label="赛事分类" width="120" align="center">
                  <template #default="scope">
                    <el-tag :type="scope.row.category && scope.row.category.includes('A') ? 'danger' : 'success'" effect="dark" round>
                      {{ scope.row.category }} 类
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="level" label="赛事级别" width="150" align="center" />
                <el-table-column prop="grade" label="获奖等次" width="150" align="center" />
                <el-table-column label="作者位次" width="150" align="center">
                  <template #default="scope">第 {{ scope.row.position }} 作者</template>
                </el-table-column>
                <el-table-column label="设定加分值" align="center">
                  <template #default="scope">
                    <span class="text-xl font-black text-blue-600">+ {{ scope.row.score }} 分</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" align="center">
                  <template #default="scope">
                    <el-button size="small" type="danger" plain icon="Delete" circle @click="handleDeleteRule(scope.row.id)" />
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <el-dialog v-model="ruleDialogVisible" title="配置新规则" width="500px" destroy-on-close>
              <el-form :model="newRule" label-width="100px" class="mt-4">
                <el-form-item label="赛事分类">
                  <el-select v-model="newRule.category" placeholder="如 A1, A2, B1..." style="width: 100%">
                    <el-option label="A1类 (顶尖国际/国家级)" value="A1" />
                    <el-option label="A2类 (权威国家级)" value="A2" />
                    <el-option label="A3类 (普通国家级)" value="A3" />
                    <el-option label="B1类 (顶尖省部级)" value="B1" />
                    <el-option label="B2类 (权威省部级)" value="B2" />
                    <el-option label="C类 (校级)" value="C" />
                  </el-select>
                </el-form-item>
                <el-form-item label="赛事级别">
                  <el-radio-group v-model="newRule.level">
                    <el-radio label="国家级">国家级</el-radio>
                    <el-radio label="省部级">省部级</el-radio>
                    <el-radio label="校级">校级</el-radio>
                  </el-radio-group>
                </el-form-item>
                <el-form-item label="获奖等次">
                  <el-select v-model="newRule.grade" style="width: 100%">
                    <el-option label="特等奖/最高奖" value="特等奖" />
                    <el-option label="一等奖/金奖" value="一等奖" />
                    <el-option label="二等奖/银奖" value="二等奖" />
                    <el-option label="三等奖/铜奖" value="三等奖" />
                  </el-select>
                </el-form-item>
                <el-form-item label="作者位次">
                  <el-input-number v-model="newRule.position" :min="1" :max="10" />
                </el-form-item>
                <el-form-item label="设定加分">
                  <el-input-number v-model="newRule.score" :min="0" :max="20" :step="0.5" />
                  <span class="ml-3 text-gray-400 text-sm">分</span>
                </el-form-item>
              </el-form>
              <template #footer>
                <el-button @click="ruleDialogVisible = false">取消</el-button>
                <el-button type="primary" color="#6366f1" @click="submitRule">立即生效</el-button>
              </template>
            </el-dialog>
          </div>

        </transition>
      </main>

      <el-drawer v-model="aiDrawerVisible" title="🤖 教务专属 AI 大模型舱" size="400px" direction="rtl">
        <div class="flex flex-col h-full bg-gray-50/50 -mt-5 -mx-5 px-5 pt-2">
          <div class="flex-1 overflow-y-auto space-y-4 pb-4 pr-2" ref="chatContainer">
            <div v-for="(msg, i) in chatHistory" :key="i" :class="msg.role === 'ai' ? 'flex justify-start' : 'flex justify-end'">
              <div :class="msg.role === 'ai' ? 'bg-white border border-gray-200 text-gray-800' : 'bg-[#6366f1] text-white shadow-md'" class="max-w-[85%] rounded-2xl p-3 px-4 text-sm leading-relaxed whitespace-pre-wrap">
                {{ msg.content }}
              </div>
            </div>
            <div v-if="chatLoading" class="flex justify-start">
              <div class="bg-white border border-gray-200 text-gray-500 rounded-2xl p-3 text-sm flex items-center">
                <span class="animate-bounce mr-1">.</span><span class="animate-bounce mr-1 delay-75">.</span><span class="animate-bounce delay-150">.</span> 深度分析中
              </div>
            </div>
          </div>
          <div class="pt-4 border-t border-gray-200 bg-white pb-6 px-1">
            <div class="flex items-center gap-2">
              <el-input v-model="chatInput" placeholder="问问我有没有异常偏高的加分..." @keyup.enter="sendChatMessage" class="flex-1" size="large" />
              <el-button type="primary" color="#6366f1" circle icon="Promotion" size="large" @click="sendChatMessage" :loading="chatLoading" class="shadow-md" />
            </div>
            <div class="flex gap-2 mt-3 overflow-x-auto text-xs">
              <el-button size="small" round @click="chatInput='帮我总结一下目前的审批进度'; sendChatMessage()">分析审批进度</el-button>
              <el-button size="small" round @click="chatInput='帮我查一下有没有加分超过5分的异常项'; sendChatMessage()">筛查异常项</el-button>
            </div>
          </div>
        </div>
      </el-drawer>

    </div>
  </div>
</template>

<style>
/* 侧边栏菜单样式 */
.el-menu-item.is-active { background-color: #263445 !important; border-left: 4px solid #409eff; }
.el-menu-item:hover { background-color: #263445 !important; }

/* 表格边框与滚动条美化 */
.el-table { --el-table-border-color: #ebeef5; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 4px; }
::-webkit-scrollbar-track { background: transparent; }

/* 页面切换动画 */
.fade-slide-enter-active, .fade-slide-leave-active { transition: all 0.3s ease; }
.fade-slide-enter-from { opacity: 0; transform: translateX(20px); }
.fade-slide-leave-to { opacity: 0; transform: translateX(-20px); }
</style>