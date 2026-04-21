<script setup>
import { ref, reactive, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, MagicStick, DocumentChecked, User, Lock, Message, Key, ChatLineRound, DataLine } from '@element-plus/icons-vue'
import request from '../utils/request'
import * as echarts from 'echarts'

// ==========================================
// 1. 全局状态
// ==========================================
const isLoggedIn = ref(false)
const studentInfo = reactive({ id: '', name: '' })
const currentMode = ref('login-pwd') // login-pwd, login-email, register
const activeTab = ref('dashboard')   // dashboard, apply

// ==========================================
// 2. 鉴权与登录表单
// ==========================================
const form = reactive({ student_id: '', name: '', email: '', password: '', code: '' })
const loading = ref(false)
const codeLoading = ref(false)
const countdown = ref(0)

const sendCode = async () => {
  if (!form.email) return ElMessage.warning('请先填写绑定的邮箱！')
  codeLoading.value = true
  try {
    await request.post('/auth/send-code', { email: form.email })
    ElMessage.success('验证码已发送，请查收！(测试请看后端终端)')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch (error) {} finally { codeLoading.value = false }
}

const handleSubmit = async () => {
  loading.value = true
  try {
    let res;
    if (currentMode.value === 'register') {
      res = await request.post('/auth/register', form)
      ElMessage.success(res.message)
      currentMode.value = 'login-pwd'
    } else {
      const url = currentMode.value === 'login-pwd' ? '/auth/login' : '/auth/login-email'
      res = await request.post(url, form)
      ElMessage.success(`欢迎回来，${res.name}！`)
      localStorage.setItem('token', res.token)
      studentInfo.id = form.student_id || res.student_id
      studentInfo.name = res.name
      isLoggedIn.value = true
      
      // 登录成功后，立刻拉取数据大屏
      fetchDashboard()
    }
  } catch (error) {} finally { loading.value = false }
}

const logout = () => {
  localStorage.removeItem('token')
  isLoggedIn.value = false
  form.password = ''; form.code = ''
}

// ==========================================
// 3. ECharts 数据大屏
// ==========================================
const dashData = reactive({ total_score: 0, status_count: {} })
const chartRef = ref(null)
let myChart = null

const fetchDashboard = async () => {
  try {
    const res = await request.get(`/student/dashboard/${studentInfo.id}`)
    dashData.total_score = res.total_score
    dashData.status_count = res.status_count
    
    await nextTick()
    if (chartRef.value) {
      if (!myChart) myChart = echarts.init(chartRef.value)
      const option = {
        tooltip: { trigger: 'item' },
        legend: { top: '5%', left: 'center' },
        series: [{
          name: '加分组成', type: 'pie', radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
          label: { show: false, position: 'center' },
          emphasis: { label: { show: true, fontSize: '20', fontWeight: 'bold' } },
          labelLine: { show: false },
          data: res.chart_data
        }]
      }
      myChart.setOption(option)
    }
  } catch (error) { console.error("拉取看板失败", error) }
}

// ==========================================
// 4. LangChain 专属 AI 助理
// ==========================================
const chatInput = ref('')
const chatHistory = ref([
  { role: 'ai', content: '你好！我是武理经院 AI 教务管家。你可以问我关于你加分情况的任何问题，或者让我帮你规划接下来的科研方向哦！' }
])
const chatLoading = ref(false)
const chatContainer = ref(null)

const sendChatMessage = async () => {
  if (!chatInput.value.trim()) return
  const question = chatInput.value
  chatHistory.value.push({ role: 'user', content: question })
  chatInput.value = ''
  
  await nextTick()
  if(chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight

  chatLoading.value = true
  try {
    const res = await request.post('/student/chat', { student_id: studentInfo.id, question: question })
    chatHistory.value.push({ role: 'ai', content: res.reply })
  } catch (e) {
    chatHistory.value.push({ role: 'ai', content: '系统网络波动，AI 正在重连...' })
  } finally {
    chatLoading.value = false
    await nextTick()
    if(chatContainer.value) chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

// ==========================================
// 5. AI 视觉审核上传舱
// ==========================================
const aiLoading = ref(false)
const aiResult = ref(null)
const uploadedImage = ref('')

const handleUpload = async (options) => {
  if (!options.file.type.startsWith('image/')) return ElMessage.error('只能上传图片哦！')
  uploadedImage.value = URL.createObjectURL(options.file)
  const formData = new FormData()
  formData.append('file', options.file)
  aiLoading.value = true
  aiResult.value = null
  try {
    const res = await request.post('/ai/analyze-certificate', formData, { headers: { 'Content-Type': 'multipart/form-data' }})
    ElMessage.success('🎉 视觉特征提取成功！')
    aiResult.value = res.ai_analysis 
  } catch (error) {} finally { aiLoading.value = false }
}

const submitToTeacher = async () => {
  loading.value = true
  try {
    await request.post('/student/submit-application', {
      student_id: studentInfo.id,
      award_name: aiResult.value.award_name,
      award_level: aiResult.value.award_level,
      suggested_score: aiResult.value.suggested_score,
      ai_reason: aiResult.value.reason
    })
    ElMessage.success('🚀 申请已成功提交教务处！')
    aiResult.value = null; uploadedImage.value = ''
    fetchDashboard() // 提交后刷新看板
  } catch (error) {} finally { loading.value = false }
}
</script>

<template>
  <div class="min-h-screen w-full bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex flex-col font-sans">
    
    <header class="w-full px-8 py-4 flex justify-between items-center bg-white/60 backdrop-blur-md shadow-sm fixed top-0 z-50">
      <div class="flex items-center">
        <img src="/logo.jpg" alt="Logo" class="w-10 h-10 rounded-full shadow-sm mr-3" />
        <span class="font-bold text-gray-800 text-lg tracking-tight">WUT 经管智能科研系统</span>
      </div>
      <div v-if="isLoggedIn" class="flex items-center space-x-4">
        <span class="text-sm text-gray-600">当前学生：<strong class="text-blue-600">{{ studentInfo.name }}</strong></span>
        <el-button type="danger" link @click="logout">安全退出</el-button>
      </div>
    </header>

    <main class="flex-1 flex items-center justify-center pt-20 pb-10 px-4 max-w-7xl mx-auto w-full">
      
      <transition name="el-fade-in-linear">
        <div v-if="!isLoggedIn" class="w-full max-w-md bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-white/50 relative overflow-hidden mt-10">
          
          <div class="absolute -top-20 -right-20 w-40 h-40 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20"></div>
          <div class="absolute -bottom-20 -left-20 w-40 h-40 bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20"></div>
          
          <div class="flex justify-center mb-4">
             <img src="/logo.jpg" class="w-16 h-16 rounded-full shadow-md border-2 border-white" />
          </div>
          
          <h2 class="text-2xl font-extrabold text-gray-800 mb-2 text-center">
            {{ currentMode === 'register' ? '激活学生账号' : '登录通行证' }}
          </h2>
          <p class="text-center text-gray-400 text-sm mb-8">
            {{ currentMode === 'register' ? '请确保学号姓名与教务处登记一致' : '欢迎回到 AI 科研申报平台' }}
          </p>

          <div class="flex bg-gray-100/80 backdrop-blur p-1 rounded-xl mb-6">
            <button @click="currentMode = 'login-pwd'" :class="currentMode === 'login-pwd' ? 'bg-white shadow text-blue-600' : 'text-gray-500'" class="flex-1 py-2 text-sm font-bold rounded-lg transition-all">学号密码</button>
            <button @click="currentMode = 'login-email'" :class="currentMode === 'login-email' ? 'bg-white shadow text-blue-600' : 'text-gray-500'" class="flex-1 py-2 text-sm font-bold rounded-lg transition-all">邮箱验证</button>
            <button @click="currentMode = 'register'" :class="currentMode === 'register' ? 'bg-white shadow text-green-600' : 'text-gray-500'" class="flex-1 py-2 text-sm font-bold rounded-lg transition-all">首次激活</button>
          </div>

          <div class="space-y-4">
            <template v-if="currentMode === 'register'">
              <el-input v-model="form.student_id" placeholder="真实学号 (必填)" :prefix-icon="User" size="large" />
              <el-input v-model="form.name" placeholder="真实姓名 (必填)" :prefix-icon="DocumentChecked" size="large" />
              <el-input v-model="form.email" placeholder="绑定电子邮箱 (必填)" :prefix-icon="Message" size="large" />
              <el-input v-model="form.password" type="password" placeholder="设置登录密码" show-password :prefix-icon="Lock" size="large" />
            </template>

            <template v-if="currentMode === 'login-pwd'">
              <el-input v-model="form.student_id" placeholder="学号" :prefix-icon="User" size="large" />
              <el-input v-model="form.password" type="password" placeholder="密码" show-password :prefix-icon="Lock" size="large" @keyup.enter="handleSubmit" />
            </template>

            <template v-if="currentMode === 'login-email'">
              <el-input v-model="form.email" placeholder="已绑定的电子邮箱" :prefix-icon="Message" size="large" />
              <div class="flex gap-2">
                <el-input v-model="form.code" placeholder="6位验证码" :prefix-icon="Key" size="large" @keyup.enter="handleSubmit" />
                <el-button size="large" type="primary" plain @click="sendCode" :disabled="countdown > 0" :loading="codeLoading">
                  {{ countdown > 0 ? `${countdown}s 后重发` : '获取验证码' }}
                </el-button>
              </div>
            </template>

            <el-button type="primary" size="large" class="w-full mt-4 shadow-md text-lg" @click="handleSubmit" :loading="loading" :color="currentMode === 'register' ? '#10b981' : '#3b82f6'">
              {{ currentMode === 'register' ? '验证并激活账号' : '立即进入系统' }}
            </el-button>
          </div>
        </div>
      </transition>

      <transition name="el-zoom-in-center">
        <div v-show="isLoggedIn" class="w-full bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white overflow-hidden min-h-[700px] flex flex-col mt-4">
          
          <el-tabs v-model="activeTab" class="px-8 pt-4 custom-tabs">
            <el-tab-pane name="dashboard">
              <template #label><span class="text-lg font-bold"><el-icon class="mr-1"><DataLine /></el-icon> 个人星盘</span></template>
            </el-tab-pane>
            <el-tab-pane name="apply">
              <template #label><span class="text-lg font-bold"><el-icon class="mr-1"><UploadFilled /></el-icon> 申请加分</span></template>
            </el-tab-pane>
          </el-tabs>

          <div class="flex-1 p-8 bg-gray-50/50">
            
            <div v-show="activeTab === 'dashboard'" class="grid grid-cols-1 md:grid-cols-2 gap-8 h-full">
              
              <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col hover:shadow-md transition-shadow">
                <h3 class="text-xl font-black text-gray-800 mb-2">综测总星值</h3>
                <div class="text-5xl font-black text-blue-600 mb-6 drop-shadow-md">+ {{ dashData.total_score }} <span class="text-lg text-gray-400 font-normal">分</span></div>
                
                <div class="flex gap-4 mb-6">
                  <div class="flex-1 bg-blue-50 rounded-lg p-3 text-center border border-blue-100"><div class="text-gray-500 text-xs">审核中</div><div class="font-bold text-blue-600 text-xl">{{ dashData.status_count['待审核'] || 0 }}</div></div>
                  <div class="flex-1 bg-green-50 rounded-lg p-3 text-center border border-green-100"><div class="text-gray-500 text-xs">已生效</div><div class="font-bold text-green-600 text-xl">{{ dashData.status_count['已通过'] || 0 }}</div></div>
                  <div class="flex-1 bg-red-50 rounded-lg p-3 text-center border border-red-100"><div class="text-gray-500 text-xs">已驳回</div><div class="font-bold text-red-600 text-xl">{{ dashData.status_count['已驳回'] || 0 }}</div></div>
                </div>
                
                <div ref="chartRef" class="flex-1 w-full min-h-[250px]"></div>
              </div>

              <div class="bg-white rounded-xl shadow-sm border border-gray-100 flex flex-col overflow-hidden hover:shadow-md transition-shadow">
                <div class="bg-gradient-to-r from-indigo-500 to-purple-600 p-4 text-white flex items-center">
                  <el-icon class="text-2xl mr-2"><ChatLineRound /></el-icon>
                  <div>
                    <h3 class="font-bold">AI 研创规划师</h3>
                    <p class="text-xs opacity-80">Powered by LangChain</p>
                  </div>
                </div>
                
                <div class="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-50/80" ref="chatContainer">
                  <div v-for="(msg, i) in chatHistory" :key="i" :class="msg.role === 'ai' ? 'flex justify-start' : 'flex justify-end'">
                    <div :class="msg.role === 'ai' ? 'bg-white border border-gray-200 text-gray-800' : 'bg-blue-500 text-white shadow-md'" class="max-w-[80%] rounded-2xl p-3 px-4 text-sm leading-relaxed">
                      {{ msg.content }}
                    </div>
                  </div>
                  <div v-if="chatLoading" class="flex justify-start">
                    <div class="bg-white border border-gray-200 text-gray-500 rounded-2xl p-3 text-sm flex items-center">
                      <span class="animate-bounce mr-1">.</span><span class="animate-bounce mr-1 delay-75">.</span><span class="animate-bounce delay-150">.</span> 深度思考中
                    </div>
                  </div>
                </div>
                
                <div class="p-3 border-t border-gray-100 bg-white flex items-center">
                  <el-input v-model="chatInput" placeholder="问问我你的加分进度..." @keyup.enter="sendChatMessage" class="flex-1 bg-gray-50" />
                  <el-button type="primary" circle icon="Promotion" class="ml-2 shadow-md" @click="sendChatMessage" :loading="chatLoading" />
                </div>
              </div>
            </div>

            <div v-show="activeTab === 'apply'" class="h-full animate-fade-in">
               <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div class="flex flex-col">
                  <h3 class="text-xl font-bold text-gray-700 mb-4 border-l-4 border-blue-500 pl-3">第一步：提交原件照片</h3>
                  <el-upload class="w-full" drag action="" :http-request="handleUpload" :show-file-list="false">
                    <div v-if="!uploadedImage && !aiLoading" class="py-12"><el-icon class="el-icon--upload text-blue-400"><upload-filled /></el-icon><div class="el-upload__text text-lg">拖拽或 <em class="text-blue-600 font-bold">点击上传证书</em></div></div>
                    <div v-if="aiLoading" class="py-16 flex flex-col items-center"><el-icon class="is-loading text-4xl text-blue-500 mb-4"><Loading /></el-icon><div class="text-blue-600 font-bold animate-pulse">🧠 正在唤醒大模型视觉神经...</div></div>
                    <img v-if="uploadedImage && !aiLoading" :src="uploadedImage" class="w-full h-64 object-contain rounded-lg p-2" />
                  </el-upload>
                </div>
                
                <div class="flex flex-col">
                  <h3 class="text-xl font-bold text-gray-700 mb-4 border-l-4 border-green-500 pl-3">第二步：AI 智能核验单</h3>
                  <div v-if="!aiResult && !aiLoading" class="flex-1 border-2 border-dashed border-gray-200 rounded-xl flex items-center justify-center bg-gray-50">
                    <span class="text-gray-400">等待上传材料...</span>
                  </div>
                  <div v-if="aiLoading" class="flex-1 flex"><el-skeleton :rows="6" animated /></div>
                  <div v-if="aiResult && !aiLoading" class="bg-blue-50/50 rounded-xl p-6 border border-blue-100 shadow-sm animate-fade-in">
                    <el-descriptions :column="1" border size="large">
                      <el-descriptions-item label="核验姓名"><span class="font-bold text-gray-800">{{ aiResult.student_name }}</span></el-descriptions-item>
                      <el-descriptions-item label="竞赛名称"><span class="font-bold text-blue-600">{{ aiResult.award_name }}</span></el-descriptions-item>
                      <el-descriptions-item label="获奖级别"><el-tag type="warning" effect="dark" round>🏆 {{ aiResult.award_level }}</el-tag></el-descriptions-item>
                      <el-descriptions-item label="拟定加分"><span class="text-2xl font-black text-green-500">+ {{ aiResult.suggested_score.toFixed(1) }}</span> 分</el-descriptions-item>
                    </el-descriptions>
                    <el-alert :title="aiResult.reason" type="success" show-icon :closable="false" class="mt-4 shadow-sm" />
                    <el-button type="primary" size="large" class="w-full mt-6 shadow-md" icon="DocumentChecked" @click="submitToTeacher" :loading="loading">确认无误，提交教务处</el-button>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </transition>
      
    </main>
  </div>
</template>

<style>
html, body, #app { margin: 0; padding: 0; }
.animate-fade-in { animation: fadeIn 0.4s ease-out forwards; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* 上传框透明磨砂效果 */
.el-upload-dragger { background-color: rgba(255,255,255,0.6) !important; border: 2px dashed #a0aec0 !important; border-radius: 1rem !important; transition: all 0.3s; }
.el-upload-dragger:hover { border-color: #3b82f6 !important; background-color: rgba(255,255,255,0.95) !important; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }

/* Tabs 深度美化 */
.custom-tabs .el-tabs__nav-wrap::after { display: none; }
.custom-tabs .el-tabs__item { font-size: 1.1rem; color: #64748b; padding: 0 20px; transition: all 0.3s; }
.custom-tabs .el-tabs__item.is-active { color: #2563eb; transform: translateY(-2px); }
.custom-tabs .el-tabs__active-bar { background-color: #2563eb; height: 3px; border-radius: 3px; }
</style>