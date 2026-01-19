---
name: confluence-assistant-setup
description: Set up Confluence Assistant Skills with credentials and configuration
---

# Confluence Assistant Setup

You are helping the user set up Confluence Assistant Skills. Guide them through the process conversationally.

## Step 1: Check Prerequisites

First, verify the environment:

```bash
python3 --version
```

Check if the confluence-assistant-skills-lib package is installed:
```bash
pip show confluence-assistant-skills-lib 2>/dev/null && echo "Library installed" || echo "Library missing"
```

If the library is missing, install it:
```bash
pip install confluence-assistant-skills-lib>=0.1.0
```

## Step 2: Get API Token

Tell the user they need an API token from Atlassian. Offer to open the browser:

"To connect to Confluence, you'll need an API token from Atlassian. I can open the page where you can create one.

Would you like me to open https://id.atlassian.com/manage-profile/security/api-tokens ?"

If they agree, use:
```bash
python3 -c "import webbrowser; webbrowser.open('https://id.atlassian.com/manage-profile/security/api-tokens')"
```

Guide them:
1. Click "Create API token"
2. Name it "Confluence Assistant Skills" or similar
3. Copy the token immediately (they won't see it again)

## Step 3: Collect Credentials

Ask the user for their Confluence credentials:

1. **Confluence Site URL**: Ask "What is your Confluence site URL? It should look like https://yourcompany.atlassian.net"

2. **Email**: Ask "What email address do you use to log into Confluence?"

3. **API Token**: Ask "Please paste your API token (I'll store it securely)"

## Step 4: Configure Environment Variables

Guide the user to set environment variables:

For bash/zsh (add to ~/.bashrc or ~/.zshrc):
```bash
export CONFLUENCE_SITE_URL="https://company.atlassian.net"
export CONFLUENCE_EMAIL="user@company.com"
export CONFLUENCE_API_TOKEN="their-token-here"
```

For PowerShell (add to profile):
```powershell
$env:CONFLUENCE_SITE_URL="https://company.atlassian.net"
$env:CONFLUENCE_EMAIL="user@company.com"
$env:CONFLUENCE_API_TOKEN="their-token-here"
```

After setting, reload the shell:
```bash
source ~/.bashrc  # or source ~/.zshrc
```

## Step 5: Validate Connection

Test the connection using the CLI:

```bash
confluence space list
```

Or test with a Python script:
```bash
python3 -c "
from confluence_assistant_skills_lib import get_confluence_client
client = get_confluence_client()
me = client.get('/wiki/rest/api/user/current')
print(f'Connected as: {me.get(\"displayName\", \"Unknown\")}')
"
```

## Step 6: Confirm Success

If validation succeeds, tell the user:

"Your Confluence Assistant Skills are now set up! Here's what you can do:

**Test with a space:**
```bash
confluence space list
```

**Or just ask me naturally:**
- 'Show me pages in the DOCS space'
- 'Search for pages about API documentation'
- 'Create a new page in the Engineering space'
- 'What pages did I update this week?'

I'm ready to help you with Confluence!"

## Troubleshooting

If authentication fails:
- **401 Unauthorized**: Token is incorrect or expired. Create a new one.
- **403 Forbidden**: Email doesn't match the account, or the account lacks permissions.
- **Connection error**: Check the URL is correct and reachable.

If the CLI is not found:
- Ensure the package is installed: `pip install confluence-assistant-skills`

If import errors occur:
- Ensure the library is installed: `pip install confluence-assistant-skills-lib>=0.1.0`
