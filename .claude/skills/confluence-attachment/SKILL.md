---
name: confluence-attachment
description: Manage file attachments - upload, download, list, and delete attachments
triggers:
  - attach
  - attachment
  - upload file
  - download file
  - upload attachment
  - download attachment
---

# Confluence Attachment Skill

Manage file attachments on Confluence pages.

## Available Scripts

### upload_attachment.py
Upload a file to a page.

**Usage:**
```bash
confluence attachment upload 12345 --file report.pdf
confluence attachment upload 12345 --file image.png --comment "Screenshot"
```

### download_attachment.py
Download an attachment.

**Usage:**
```bash
confluence attachment download ATTACHMENT_ID --output ./downloads/
confluence attachment download 12345 --all  # Download all from page
```

### list_attachments.py
List attachments on a page.

**Usage:**
```bash
confluence attachment list 12345
confluence attachment list 12345 --output json
```

### delete_attachment.py
Remove an attachment.

**Usage:**
```bash
confluence attachment delete ATTACHMENT_ID
confluence attachment delete ATTACHMENT_ID --force
```

### update_attachment.py
Replace an attachment file.

**Usage:**
```bash
confluence attachment update ATTACHMENT_ID --file new_version.pdf
```
