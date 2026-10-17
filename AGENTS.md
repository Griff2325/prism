# Lighting harness project instructions

Keep the adapter/core/source boundary explicit. Implement against official protocols and report physical validation separately from mocks. No DRM, HDCP, secure-surface bypass, account scraping, or fabricated capture results.

Default runs are previews. Never discover continuously or send light changes without explicit device selection and live opt-in. Preserve bounded input sizes, watchdogs, monotonic smoothing and output rate caps. Keep private addresses, device IDs, account data and credentials only under ignored .local/. Do not commit discovery results, placement photos or private handoffs.

Keep docs technical. No resume case studies or rewritten/backdated history. Run unittest and preview verification before committing. New network input endpoints require explicit authentication, bounded traffic, and opt-in; prefer zone colors over full images.
