/**
 * 全局错误边界组件
 * 捕获子组件树中的 JavaScript 错误，显示友好的错误页面
 */
import React from 'react';
import { Result, Button } from 'antd';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
          <Result
            status="error"
            title="页面出错了"
            subTitle="抱歉，页面发生了意外错误。请尝试返回首页。"
            extra={
              <Button type="primary" onClick={this.handleReset}>
                返回首页
              </Button>
            }
          />
        </div>
      );
    }
    return this.props.children;
  }
}
