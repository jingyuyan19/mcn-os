#!/bin/bash
# Add OpenAI News as a new source in Sanity

PROJECT_ID="4t6f8tmh"
API_TOKEN="skNfoTE6nT4cO7t9jj1fRtqL86MJyXKCvLpUWut3q0y1oZQwnQEHz5og38NrYtw7qj5VAeUgSGvDxQmVcgqJzzXrtdwfUrDLtF8GSr4MQ00DJLsTdNmfgkHjmynoiPqrUPEAWeBbIf2bsHS5fezjBqUnnwjMtzQmCcxmCOsVsNFTAE5kBvXP"

curl -X POST "https://${PROJECT_ID}.api.sanity.io/v2024-01-01/data/mutate/production" \
  -H "Authorization: Bearer ${API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "mutations": [
      {
        "create": {
          "_type": "source",
          "name": "OpenAI News",
          "url": "https://openai.com/news/",
          "platform": "web",
          "extraction_config": {
            "ai_instruction": "Extract the latest news and announcements from OpenAI. Focus on product launches, research papers, and major updates.",
            "max_items": 5,
            "method": "firecrawl"
          }
        }
      }
    ]
  }'

echo ""
echo "OpenAI News source added!"
