---
name: confluence-attachment
description: Manage file attachments - upload, download, list, and delete attachments. ALWAYS use when user wants to work with files on pages.
triggers:
  - attach
  - attachment
  - upload file
  - download file
  - upload attachment
  - download attachment
  - file
  - files
---

# Confluence Attachment Skill

Manage file attachments on Confluence pages.

---

## ⚠️ PRIMARY USE CASE

**This skill manages files attached to Confluence pages.** Use for:
- Uploading files to pages
- Downloading attachments
- Listing files on a page
- Deleting attachments

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Upload/download files | - |
| List page attachments | - |
| Delete attachments | - |
| Create/edit pages | `confluence-page` |
| Search for content | `confluence-search` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List/download | - | Read-only |
| Upload | - | Can be deleted |
| Update | ⚠️ | Replaces existing file |
| Delete | ⚠️⚠️ | **No recovery** |

---

## CLI Commands

### confluence attachment upload
Upload a file to a page.

**Usage:**
```bash
confluence attachment upload PAGE_ID FILE_PATH
confluence attachment upload 12345 report.pdf
confluence attachment upload 12345 image.png --comment "Screenshot"
```

### confluence attachment download
Download an attachment.

**Usage:**
```bash
confluence attachment download ATTACHMENT_ID --output ./downloads/
confluence attachment download att123456 --output myfile.pdf
confluence attachment download 12345 --all --output ./downloads/  # Download all from page
```

### confluence attachment list
List attachments on a page.

**Usage:**
```bash
confluence attachment list 12345
confluence attachment list 12345 --output json
confluence attachment list 12345 --output table
confluence attachment list 12345 --media-type application/pdf
```

### confluence attachment delete
Remove an attachment.

**Usage:**
```bash
confluence attachment delete ATTACHMENT_ID
confluence attachment delete ATTACHMENT_ID --force
```

### confluence attachment update
Replace an attachment file.

**Usage:**
```bash
confluence attachment update ATTACHMENT_ID FILE_PATH
confluence attachment update att123456 new_version.pdf
confluence attachment update att123456 updated.docx --comment "Updated content"
```
