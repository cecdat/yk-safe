import React from 'react';
import { Space, Switch, Segmented, message, Tooltip } from 'antd';
import { CheckOutlined, CloseOutlined, SafetyOutlined, FireOutlined } from '@ant-design/icons';
import { getFirewallConfig, startFirewall, stopFirewall, updateFirewallMode } from '../api/firewall';

const FirewallModeSwitch = ({ status, setStatus, config, setConfig }) => {
  const handleStatusChange = async (isRunning) => {
    try {
      if (isRunning) {
        await startFirewall();
        message.success('防火墙已成功启动');
      } else {
        await stopFirewall();
        message.success('防火墙已成功停止');
      }
      setStatus((prev) => ({ ...prev, is_running: isRunning }));
    } catch (error) {
      message.error(`操作失败: ${error.message || '服务器错误'}`);
    }
  };

  const handleModeChange = async (mode) => {
    try {
      await updateFirewallMode(mode, `切换到${mode === 'whitelist' ? '白名单' : '黑名单'}模式`);
      message.success(`防火墙模式已切换到${mode === 'whitelist' ? '白名单' : '黑名单'}模式`);
      setConfig((prev) => ({ ...prev, mode }));
    } catch (error) {
      message.error(`模式切换失败: ${error.message || '服务器错误'}`);
    }
  };

  return (
    <Space size="middle">
      <Tooltip title={status?.is_running ? "关闭防火墙" : "启动防火墙"}>
        <Switch
          checkedChildren={<CheckOutlined />}
          unCheckedChildren={<CloseOutlined />}
          checked={status?.is_running}
          onChange={handleStatusChange}
          loading={status === null}
          size="small"
        />
      </Tooltip>
      <Segmented
        options={[
          { label: '黑名单', value: 'blacklist', icon: <FireOutlined /> },
          { label: '白名单', value: 'whitelist', icon: <SafetyOutlined /> },
        ]}
        value={config?.mode}
        onChange={handleModeChange}
        disabled={!status?.is_running}
        size="small"
      />
    </Space>
  );
};

export default FirewallModeSwitch;
