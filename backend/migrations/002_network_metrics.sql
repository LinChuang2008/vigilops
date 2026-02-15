-- Add network bandwidth and packet loss columns
ALTER TABLE host_metrics ADD COLUMN IF NOT EXISTS net_send_rate_kb DOUBLE PRECISION;
ALTER TABLE host_metrics ADD COLUMN IF NOT EXISTS net_recv_rate_kb DOUBLE PRECISION;
ALTER TABLE host_metrics ADD COLUMN IF NOT EXISTS net_packet_loss_rate DOUBLE PRECISION;
