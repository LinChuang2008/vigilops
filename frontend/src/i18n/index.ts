/**
 * 国际化配置 (Internationalization Configuration)
 * 
 * 使用 react-i18next 实现多语言支持
 * 支持语言：中文(zh)、英文(en)
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// 导入语言资源
import zh from './locales/zh';
import en from './locales/en';

export type SupportedLanguage = 'zh' | 'en';

// 从localStorage获取用户语言偏好，默认中文
const savedLanguage = localStorage.getItem('language') || 'zh';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      zh: { translation: zh },
      en: { translation: en },
    },
    lng: savedLanguage, // 默认语言
    fallbackLng: 'zh', // 回退语言
    
    interpolation: {
      escapeValue: false, // React 已经默认转义
    },

    // 调试选项
    debug: false,
    
    // 命名空间
    defaultNS: 'translation',
    
    // 检测选项
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;