# arxiv-digest API Key Setup

## The Issue
The cron job was failing because `ANTHROPIC_API_KEY` wasn't available in the isolated session. The OAuth tokens in OpenClaw config don't work for direct API calls.

## The Fix
Updated the pipeline to:
1. Try multiple API providers (Anthropic direct, foxcode-claude proxy, OpenAI)
2. Fall back to "manual review" mode if no API key is available
3. Handle "Other / Needs Review" papers in Discord output

## Files Modified
- `src/judge_relevance.py` - Multi-provider support with fallback
- `src/config.py` - Load `.secret/anthropic.env` and `.secret/openai.env`
- `src/digest_writer.py` - Handle "Other / Needs Review" theme

## To Enable Automatic Judging

### Option 1: Anthropic API (Recommended)
1. Get API key from https://console.anthropic.com/settings/keys
2. Copy the example file: `cp .secret/anthropic.env.example .secret/anthropic.env`
3. Add your key: `ANTHROPIC_API_KEY=sk-ant-api03-...`

### Option 2: OpenAI API
Create `.secret/openai.env`:
```
OPENAI_API_KEY=sk-...
```

### Option 3: Cron Job Environment
Add to the cron job config:
```json
"env": {
  "ANTHROPIC_API_KEY": "sk-ant-api03-..."
}
```

## Testing
Run the full pipeline manually:
```bash
source .venv/bin/activate
python src/main.py fetch
python src/main.py judge
python src/main.py discord --relevance data/relevance.json
python src/main.py process --relevance data/relevance.json
```

## Fallback Mode
If no API key is configured, all papers are marked as "relevant" with theme "Needs Review" so you don't miss anything. They'll appear under "📝 Other / Needs Review" in Discord.
