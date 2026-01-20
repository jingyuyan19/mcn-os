// Schema: Topic (选题)
// Central data model for Perception Layer
// Aggregates signals from multiple sources into unified topics

export default {
    name: 'topic',
    title: '📰 选题',
    type: 'document',
    groups: [
        { name: 'core', title: '📝 核心信息' },
        { name: 'signals', title: '📡 信号聚合' },
        { name: 'analysis', title: '🔍 分析结果' },
        { name: 'matching', title: '🎯 匹配分配' },
        { name: 'feedback', title: '📊 效果反馈' }
    ],
    fields: [
        // === Core Info ===
        {
            name: 'title',
            group: 'core',
            title: '核心议题',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'source_type',
            group: 'core',
            title: '来源类型',
            type: 'string',
            options: {
                list: [
                    { title: '🕷️ 社交爬虫', value: 'social_crawler' },
                    { title: '📚 知识库', value: 'knowledge_base' },
                    { title: '📰 RSS订阅', value: 'rss_feed' },
                    { title: '✋ 人工注入', value: 'manual' }
                ]
            },
            initialValue: 'social_crawler'
        },
        {
            name: 'status',
            group: 'core',
            title: '状态',
            type: 'string',
            options: {
                list: [
                    { title: '🆕 新建', value: 'new' },
                    { title: '🔄 分析中', value: 'analyzing' },
                    { title: '✅ 已审核', value: 'approved' },
                    { title: '❌ 已拒绝', value: 'rejected' },
                    { title: '📝 已生成脚本', value: 'scripted' }
                ]
            },
            initialValue: 'new'
        },
        {
            name: 'keywords',
            group: 'core',
            title: '关键词',
            type: 'array',
            of: [{ type: 'string' }],
            options: { layout: 'tags' }
        },

        // === Signal Aggregation (Deep Think consensus) ===
        {
            name: 'signals',
            group: 'signals',
            title: '聚合信号',
            type: 'array',
            of: [{
                type: 'object',
                fields: [
                    {
                        name: 'platform',
                        title: '平台',
                        type: 'string',
                        options: {
                            list: [
                                { title: '小红书', value: 'xhs' },
                                { title: '抖音', value: 'douyin' },
                                { title: '微博', value: 'weibo' },
                                { title: 'B站', value: 'bilibili' },
                                { title: '知乎', value: 'zhihu' },
                                { title: 'RSS', value: 'rss' },
                                { title: '手动', value: 'manual' }
                            ]
                        }
                    },
                    { name: 'url', title: 'URL', type: 'url' },
                    { name: 'content_snippet', title: '内容摘要', type: 'text', rows: 3 },
                    {
                        name: 'metrics',
                        title: '指标快照',
                        type: 'object',
                        fields: [
                            { name: 'likes', title: '点赞', type: 'number' },
                            { name: 'comments', title: '评论', type: 'number' },
                            { name: 'shares', title: '分享', type: 'number' },
                            { name: 'captured_at', title: '采集时间', type: 'datetime' }
                        ]
                    }
                ],
                preview: {
                    select: { platform: 'platform', url: 'url', likes: 'metrics.likes' },
                    prepare({ platform, url, likes }: any) {
                        return {
                            title: `${platform || 'unknown'} - ${likes || 0} likes`,
                            subtitle: url
                        }
                    }
                }
            }],
            description: '多平台/多来源的聚合信号'
        },

        // === Analysis Results (BettaFish) ===
        {
            name: 'z_score_velocity',
            group: 'analysis',
            title: 'Z-Score 热度',
            type: 'number',
            description: '相对于平台基线的标准化热度分数'
        },
        {
            name: 'controversy_ratio',
            group: 'analysis',
            title: '争议率',
            type: 'number',
            description: '评论/点赞比率，高于0.1表示争议性话题'
        },
        {
            name: 'sentiment',
            group: 'analysis',
            title: '情感倾向',
            type: 'string',
            options: {
                list: [
                    { title: '😊 正面', value: 'positive' },
                    { title: '😠 负面', value: 'negative' },
                    { title: '😐 中性', value: 'neutral' },
                    { title: '🔥 争议', value: 'controversial' }
                ]
            }
        },
        {
            name: 'extracted_hooks',
            group: 'analysis',
            title: '神评/钩子',
            type: 'array',
            of: [{ type: 'string' }],
            description: 'BettaFish从评论区提取的高价值观点'
        },
        {
            name: 'bettafish_summary',
            group: 'analysis',
            title: 'BettaFish分析摘要',
            type: 'text',
            rows: 4
        },

        // === Artist Matching ===
        {
            name: 'niche',
            group: 'matching',
            title: '关联赛道',
            type: 'reference',
            to: [{ type: 'nicheConfig' }]
        },
        {
            name: 'assigned_artist',
            group: 'matching',
            title: '分配艺人',
            type: 'reference',
            to: [{ type: 'artist' }]
        },
        {
            name: 'match_reasoning',
            group: 'matching',
            title: '匹配理由',
            type: 'string',
            description: '为什么选择此艺人'
        },

        // === Deduplication ===
        {
            name: 'fingerprint',
            group: 'signals',
            title: 'Dedup指纹',
            type: 'string',
            readOnly: true,
            description: '用于去重的语义指纹'
        },

        // === Feedback Loop ===
        {
            name: 'generated_post',
            group: 'feedback',
            title: '生成的帖子',
            type: 'reference',
            to: [{ type: 'post' }]
        },
        {
            name: 'performance',
            group: 'feedback',
            title: '实际表现',
            type: 'object',
            description: '发布后的实际效果数据（用于反馈优化）',
            fields: [
                { name: 'actual_views', title: '实际播放量', type: 'number' },
                { name: 'actual_likes', title: '实际点赞', type: 'number' },
                { name: 'actual_comments', title: '实际评论', type: 'number' },
                { name: 'actual_shares', title: '实际分享', type: 'number' },
                { name: 'ctr', title: '点击率 (CTR %)', type: 'number', description: '展现/点击比率' },
                { name: 'avg_watch_time', title: '平均观看时长 (秒)', type: 'number' },
                { name: 'completion_rate', title: '完播率 (%)', type: 'number', description: '完整观看视频的比例' },
                { name: 'measured_at', title: '测量时间', type: 'datetime' },
                { name: 'accuracy_ratio', title: '预测准确率', type: 'number', description: '预测热度 vs 实际热度' }
            ]
        }
    ],
    preview: {
        select: {
            title: 'title',
            source: 'source_type',
            status: 'status',
            velocity: 'z_score_velocity',
            artistName: 'assigned_artist.name'
        },
        prepare({ title, source, status, velocity, artistName }: any) {
            const sourceIcon: Record<string, string> = {
                social_crawler: '🕷️',
                knowledge_base: '📚',
                rss_feed: '📰',
                manual: '✋'
            }
            const statusIcon: Record<string, string> = {
                new: '🆕',
                analyzing: '🔄',
                approved: '✅',
                rejected: '❌',
                scripted: '📝'
            }
            return {
                title: `${sourceIcon[source] || '❓'} ${title}`,
                subtitle: `${statusIcon[status] || status} | 热度: ${velocity?.toFixed(1) || 'N/A'} | ${artistName || '未分配'}`
            }
        }
    },
    orderings: [
        {
            title: '热度 (高→低)',
            name: 'velocityDesc',
            by: [{ field: 'z_score_velocity', direction: 'desc' }]
        },
        {
            title: '创建时间 (新→旧)',
            name: 'createdAtDesc',
            by: [{ field: '_createdAt', direction: 'desc' }]
        }
    ]
}
