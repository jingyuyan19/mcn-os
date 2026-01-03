// Schema: Source (情报监听源)
// RSS, API, or web scraping sources with extraction config

export default {
    name: 'source',
    title: '📡 情报监听源',
    type: 'document',
    fields: [
        {
            name: 'name',
            title: '来源名称',
            type: 'string',
            validation: (Rule: any) => Rule.required(),
            description: '例: 36Kr 快讯, 央视新闻 RSS'
        },
        {
            name: 'category',
            title: '赛道分类',
            type: 'string',
            options: {
                list: [
                    { title: '财经', value: 'finance' },
                    { title: '科技', value: 'tech' },
                    { title: '儿童', value: 'kids' },
                    { title: '玄学', value: 'metaphysics' },
                    { title: '时政', value: 'politics' },
                    { title: '全品类', value: 'all' }
                ]
            },
            validation: (Rule: any) => Rule.required(),
            description: '🛡️ 防呆核心：用于后续过滤艺人，防止财经艺人读儿歌'
        },
        {
            name: 'url',
            title: '监测地址 (URL/RSS)',
            type: 'url',
            validation: (Rule: any) => Rule.uri({ scheme: ['http', 'https'] }).required()
        },
        {
            name: 'extraction_config',
            title: '提取策略',
            type: 'object',
            fields: [
                {
                    name: 'method',
                    title: '抓取方式',
                    type: 'string',
                    options: {
                        list: [
                            { title: 'Firecrawl (智能全文)', value: 'firecrawl' },
                            { title: 'RSS Feed', value: 'rss' },
                            { title: 'Twitter API', value: 'twitter' }
                        ]
                    },
                    initialValue: 'firecrawl'
                },
                {
                    name: 'ai_instruction',
                    title: '🕵️‍♀️ 猎手指令 (致 DeepSeek)',
                    type: 'text',
                    rows: 3,
                    description: '告诉 AI 重点看什么。例："只关注利好新能源板块的内容，忽略广告。"'
                },
                {
                    name: 'max_items',
                    title: '每次抓取数量',
                    type: 'number',
                    initialValue: 5
                }
            ]
        }
    ],
    preview: {
        select: {
            title: 'name',
            subtitle: 'category'
        },
        prepare({ title, subtitle }: { title: string; subtitle: string }) {
            const categoryMap: Record<string, string> = {
                finance: '💰 财经',
                tech: '🔬 科技',
                kids: '🧒 儿童',
                metaphysics: '🔮 玄学',
                politics: '🏛️ 时政',
                all: '🌐 全品类'
            }
            return {
                title: title,
                subtitle: categoryMap[subtitle] || subtitle
            }
        }
    }
}
