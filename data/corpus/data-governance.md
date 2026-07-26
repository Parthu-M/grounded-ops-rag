# Nimbus Data Governance.

Nimbus encrypts stored customer data with AES-256 and encrypts network traffic with TLS 1.3. Production backups are created every six hours. Backups are retained for 30 days and are encrypted with keys separate from the primary data keys. Restore exercises are performed once per quarter.

Audit log events are retained for 365 days on Enterprise and 90 days on Team. Starter does not include an organization audit log. Customers can export audit events in newline-delimited JSON. Exported records contain the actor, action, target, source IP address, and event timestamp.

When a project is deleted, it enters a seven-day recoverable state. After that state ends, primary data is purged within 30 days. Backup copies age out under the normal 30-day backup retention window. Customers may choose the United States or European Union as their primary data region, but cross-region project moves require a support request.

