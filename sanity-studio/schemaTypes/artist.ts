// Schema: Artist (艺人档案)
// Core entity that references all base assets
// Groups: DNA, Visuals, Config

export default {
    name: 'artist',
    title: '🎭 艺人档案',
    type: 'document',
    groups: [
        { name: 'dna', title: '🧬 基础 DNA' },
        { name: 'visuals', title: '📸 视觉母版' },
        { name: 'config', title: '⚙️ 生产配置' }
    ],
    fields: [
        // === Group 1: DNA ===
        {
            name: 'name',
            group: 'dna',
            title: '艺名',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'niche',
            group: 'dna',
            title: '赛道',
            type: 'string',
            options: {
                list: [
                    { title: '财经', value: 'finance' },
                    { title: '科技', value: 'tech' },
                    { title: '儿童', value: 'kids' },
                    { title: '玄学', value: 'metaphysics' }
                ]
            },
            validation: (Rule: any) => Rule.required(),
            description: '快速选择 - 使用下方赛道配置获取更多控制'
        },
        {
            name: 'nicheConfig',
            group: 'dna',
            title: '赛道配置 (高级)',
            type: 'reference',
            to: [{ type: 'nicheConfig' }],
            description: '关联赛道配置以启用关键词监控和自动爬取'
        },
        {
            name: 'backstory',
            group: 'dna',
            title: '人设背景',
            type: 'text',
            rows: 4,
            description: '角色的背景故事、性格特点、说话风格等'
        },
        {
            name: 'subtitle',
            group: 'dna',
            title: '副标题/定位',
            type: 'string',
            description: '如：科技数码达人、财经分析师'
        },
        {
            name: 'voiceStyle',
            group: 'dna',
            title: '语言风格',
            type: 'string',
            options: {
                list: [
                    { title: '专业', value: 'professional' },
                    { title: '轻松', value: 'casual' },
                    { title: '幽默', value: 'humorous' },
                    { title: '严肃', value: 'serious' }
                ]
            },
            description: '内容输出的整体风格基调'
        },
        {
            name: 'contentFocus',
            group: 'dna',
            title: '内容方向',
            type: 'array',
            of: [{ type: 'string' }],
            description: '擅长的内容领域，如：手机评测、AI技术、股票分析'
        },
        {
            name: 'excludeKeywords',
            group: 'dna',
            title: '排除关键词',
            type: 'array',
            of: [{ type: 'string' }],
            description: '不适合此艺人的关键词，用于过滤选题'
        },

        // === Group 2: Visuals (一次性设计 - Midjourney/Nano Banana Pro) ===
        {
            name: 'master_visuals',
            group: 'visuals',
            title: '视觉母版 (不可变)',
            type: 'object',
            fields: [
                {
                    name: 'face_anchor',
                    title: '🎥 锁脸特写 (Face Anchor)',
                    type: 'image',
                    options: { hotspot: true },
                    description: '⚠️ 必须是 1:1 正方形高清图，仅含人脸。用于 PuLID 锁脸。',
                    validation: (Rule: any) => Rule.required().error('锁脸图是必填项！')
                },
                {
                    name: 'full_body',
                    title: '全身立绘',
                    type: 'image',
                    options: { hotspot: true }
                },
                {
                    name: 'three_views',
                    title: '三视图 (正/侧/背)',
                    type: 'image',
                    options: { hotspot: true }
                },
                {
                    name: 'poses',
                    title: '常用姿势库',
                    type: 'array',
                    of: [{ type: 'image' }]
                }
            ]
        },

        // === Group 3: Config ===
        {
            name: 'voice',
            group: 'config',
            title: '音色',
            type: 'reference',
            to: [{ type: 'voice' }],
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'available_wardrobes',
            group: 'config',
            title: '专属衣橱',
            type: 'array',
            of: [{ type: 'reference', to: [{ type: 'wardrobe' }] }],
            description: '此艺人可使用的服装列表'
        },
        {
            name: 'studio_images',
            group: 'visuals',
            title: '影棚背景图',
            type: 'array',
            of: [{ type: 'image', options: { hotspot: true } }],
            description: '此艺人专属影棚的背景图（可多张）'
        },
        {
            name: 'default_sources',
            group: 'config',
            title: '默认关注源',
            type: 'array',
            of: [{
                type: 'reference',
                to: [{ type: 'source' }]
                // Note: Ideally filter by niche, but Sanity's filter is complex for array references
                // We'll validate this in n8n/middleware instead
            }],
            description: '日常监听的情报源'
        },

        // === Perception Layer v3.0: Dynamic Scoring Weights ===
        {
            name: 'scoringWeights',
            group: 'config',
            title: '⚖️ 选题评分权重',
            type: 'object',
            description: '控制选题排序算法中各因素的权重',
            fields: [
                {
                    name: 'recency',
                    title: '时效性权重',
                    type: 'number',
                    initialValue: 0.30,
                    description: '新闻类艺人设高，教育类设低'
                },
                {
                    name: 'relevance',
                    title: '相关性权重',
                    type: 'number',
                    initialValue: 0.35,
                    description: '与艺人定位的匹配度'
                },
                {
                    name: 'source_priority',
                    title: '来源权重',
                    type: 'number',
                    initialValue: 0.15,
                    description: '优质来源（如一级媒体）的额外加成'
                },
                {
                    name: 'novelty',
                    title: '新颖度权重',
                    type: 'number',
                    initialValue: 0.20,
                    description: '与已发布内容的差异度'
                }
            ]
        },

        // === Perception Layer v3.0: Knowledge Base Curriculum ===
        {
            name: 'knowledgeBase',
            group: 'config',
            title: '📚 知识库配置',
            type: 'object',
            description: '教育类艺人的知识库课程进度',
            fields: [
                {
                    name: 'notebookId',
                    title: 'Open Notebook ID',
                    type: 'string',
                    description: '关联的Open Notebook知识库ID'
                },
                {
                    name: 'curriculumMode',
                    title: '课程模式',
                    type: 'boolean',
                    initialValue: false,
                    description: '启用系统化课程进度跟踪'
                },
                {
                    name: 'curriculumProgress',
                    title: '课程进度',
                    type: 'array',
                    of: [{
                        type: 'object',
                        fields: [
                            { name: 'chapterId', title: '章节ID', type: 'string' },
                            {
                                name: 'status',
                                title: '状态',
                                type: 'string',
                                options: {
                                    list: [
                                        { title: '待处理', value: 'pending' },
                                        { title: '进行中', value: 'in_progress' },
                                        { title: '已完成', value: 'completed' }
                                    ]
                                }
                            },
                            { name: 'videoId', title: '生成的视频', type: 'reference', to: [{ type: 'post' }] },
                            { name: 'completedAt', title: '完成时间', type: 'datetime' }
                        ]
                    }]
                }
            ]
        }
    ],
    preview: {
        select: {
            title: 'name',
            subtitle: 'niche',
            media: 'master_visuals.face_anchor'
        },
        prepare({ title, subtitle, media }: { title: string; subtitle: string; media: any }) {
            const nicheMap: Record<string, string> = {
                finance: '💰 财经',
                tech: '🔬 科技',
                kids: '🧒 儿童',
                metaphysics: '🔮 玄学'
            }
            return {
                title: title,
                subtitle: nicheMap[subtitle] || subtitle,
                media: media
            }
        }
    }
}
