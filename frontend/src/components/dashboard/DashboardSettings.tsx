/**
 * Dashboard 设置面板组件
 * 提供组件显示/隐藏控制和布局设置
 */
import { useState } from 'react';
import {
  Drawer, List, Switch, Button, Space, Typography, Divider,
  InputNumber, Select, message
} from 'antd';
import {
  SettingOutlined, EyeOutlined, EyeInvisibleOutlined,
  ReloadOutlined, DownloadOutlined, UploadOutlined
} from '@ant-design/icons';
import type { DashboardConfig } from './types';

const { Title, Text } = Typography;

interface DashboardSettingsProps {
  visible: boolean;
  config: DashboardConfig;
  onClose: () => void;
  onConfigChange: (config: DashboardConfig) => void;
  onResetLayout: () => void;
}

export default function DashboardSettings({
  visible,
  config,
  onClose,
  onConfigChange,
  onResetLayout,
}: DashboardSettingsProps) {
  const [localConfig, setLocalConfig] = useState<DashboardConfig>(config);

  // 切换组件可见性
  const toggleWidgetVisibility = (widgetId: string, visible: boolean) => {
    const updatedWidgets = localConfig.layout.widgets.map(widget =>
      widget.id === widgetId ? { ...widget, visible } : widget
    );
    
    const newConfig = {
      ...localConfig,
      layout: {
        ...localConfig.layout,
        widgets: updatedWidgets,
        lastModified: Date.now()
      }
    };
    
    setLocalConfig(newConfig);
    onConfigChange(newConfig);
  };

  // 更新设置
  const updateSettings = (key: string, value: any) => {
    const newConfig = {
      ...localConfig,
      settings: {
        ...localConfig.settings,
        [key]: value
      }
    };
    
    setLocalConfig(newConfig);
    onConfigChange(newConfig);
  };

  // 导出配置
  const exportConfig = () => {
    const dataStr = JSON.stringify(localConfig, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `dashboard-config-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    
    URL.revokeObjectURL(url);
    message.success('配置导出成功');
  };

  // 导入配置
  const importConfig = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const importedConfig = JSON.parse(event.target?.result as string);
          setLocalConfig(importedConfig);
          onConfigChange(importedConfig);
          message.success('配置导入成功');
        } catch (error) {
          message.error('配置文件格式错误');
        }
      };
      reader.readAsText(file);
    };
    
    input.click();
  };

  const visibleWidgets = localConfig.layout.widgets.filter(w => w.visible);
  const hiddenWidgets = localConfig.layout.widgets.filter(w => !w.visible);

  return (
    <Drawer
      title={
        <Space>
          <SettingOutlined />
          仪表盘设置
        </Space>
      }
      placement="right"
      width={400}
      open={visible}
      onClose={onClose}
      styles={{
        body: { padding: '16px 24px' }
      }}
    >
      {/* 组件显示控制 */}
      <Title level={5}>组件显示</Title>
      <Text type="secondary">控制各组件的显示和隐藏</Text>
      
      {visibleWidgets.length > 0 && (
        <>
          <Divider orientationMargin="left" style={{ margin: '12px 0 8px' }}>
            <Space>
              <EyeOutlined style={{ color: '#52c41a' }} />
              <Text style={{ color: '#52c41a', fontSize: 12 }}>显示中 ({visibleWidgets.length})</Text>
            </Space>
          </Divider>
          
          <List
            size="small"
            dataSource={visibleWidgets}
            renderItem={(widget) => (
              <List.Item
                actions={[
                  <Switch
                    key="switch"
                    size="small"
                    checked={true}
                    onChange={(checked) => toggleWidgetVisibility(widget.id, checked)}
                  />
                ]}
              >
                <Text>{widget.title}</Text>
              </List.Item>
            )}
          />
        </>
      )}
      
      {hiddenWidgets.length > 0 && (
        <>
          <Divider orientationMargin="left" style={{ margin: '12px 0 8px' }}>
            <Space>
              <EyeInvisibleOutlined style={{ color: '#999' }} />
              <Text style={{ color: '#999', fontSize: 12 }}>已隐藏 ({hiddenWidgets.length})</Text>
            </Space>
          </Divider>
          
          <List
            size="small"
            dataSource={hiddenWidgets}
            renderItem={(widget) => (
              <List.Item
                actions={[
                  <Switch
                    key="switch"
                    size="small"
                    checked={false}
                    onChange={(checked) => toggleWidgetVisibility(widget.id, checked)}
                  />
                ]}
              >
                <Text type="secondary">{widget.title}</Text>
              </List.Item>
            )}
          />
        </>
      )}

      <Divider />

      {/* 布局设置 */}
      <Title level={5}>布局设置</Title>
      
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Text>网格列数</Text>
          <InputNumber
            style={{ width: '100%', marginTop: 4 }}
            value={localConfig.settings.gridCols}
            min={6}
            max={24}
            onChange={(value) => updateSettings('gridCols', value || 12)}
          />
        </div>
        
        <div>
          <Text>行高 (px)</Text>
          <InputNumber
            style={{ width: '100%', marginTop: 4 }}
            value={localConfig.settings.rowHeight}
            min={30}
            max={120}
            onChange={(value) => updateSettings('rowHeight', value || 60)}
          />
        </div>
        
        <div>
          <Text>紧凑模式</Text>
          <Select
            style={{ width: '100%', marginTop: 4 }}
            value={localConfig.settings.compactType}
            onChange={(value) => updateSettings('compactType', value)}
            options={[
              { label: '垂直紧凑', value: 'vertical' },
              { label: '水平紧凑', value: 'horizontal' },
              { label: '关闭紧凑', value: null }
            ]}
          />
        </div>
        
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Text>自动保存</Text>
          <Switch
            checked={localConfig.settings.autoSave}
            onChange={(checked) => updateSettings('autoSave', checked)}
          />
        </div>
      </Space>

      <Divider />

      {/* 操作按钮 */}
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Button 
          block 
          icon={<ReloadOutlined />} 
          onClick={onResetLayout}
        >
          重置为默认布局
        </Button>
        
        <Button 
          block 
          icon={<DownloadOutlined />} 
          onClick={exportConfig}
        >
          导出配置
        </Button>
        
        <Button 
          block 
          icon={<UploadOutlined />} 
          onClick={importConfig}
        >
          导入配置
        </Button>
      </Space>

      <Divider />

      {/* 配置信息 */}
      <Text type="secondary" style={{ fontSize: 12 }}>
        最后修改: {new Date(localConfig.layout.lastModified).toLocaleString()}
      </Text>
    </Drawer>
  );
}