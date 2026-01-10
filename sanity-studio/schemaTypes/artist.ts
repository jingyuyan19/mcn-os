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
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'backstory',
            group: 'dna',
            title: '人设背景',
            type: 'text',
            rows: 4,
            description: '角色的背景故事、性格特点、说话风格等'
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
