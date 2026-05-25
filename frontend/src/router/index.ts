import { createRouter, createWebHashHistory } from 'vue-router'

import DataCenter from '../pages/DataCenter.vue'
import ReportWorkbench from '../pages/ReportWorkbench.vue'
import Settings from '../pages/Settings.vue'
import TodayOverview from '../pages/TodayOverview.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'today',
      component: TodayOverview,
      meta: {
        title: '今日总览'
      }
    },
    {
      path: '/data',
      name: 'data-center',
      component: DataCenter,
      meta: {
        title: '数据中心'
      }
    },
    {
      path: '/reports',
      name: 'report-workbench',
      component: ReportWorkbench,
      meta: {
        title: '日报工作台'
      }
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings,
      meta: {
        title: '设置'
      }
    },
    {
      path: '/dashboard',
      redirect: '/'
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

export default router
