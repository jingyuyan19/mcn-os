// Schema: Post (视频工单)
// The core production workflow with storyboard editing
// ⚠️ Critical Fix: GROQ filter for wardrobe/studio selection
// ⚠️ Critical Fix: is_locked prevents AI overwriting human edits

export default {
    name: 'post',
    title: '🎬 视频工单',
    type: 'document',
    groups: [
        { name: 'config', title: '🛠️ 配置' },
        { name: 'storyboard', title: '🎞️ 分镜脚本' },
        { name: 'meta', title: '📊 状态' }
    ],
    fields: [
        // === Group 1: Config ===
        {
            name: 'title',
            group: 'config',
            title: '工单标题',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'artist',
            group: 'config',
            title: '执行艺人',
            type: 'reference',
            to: [{ type: 'artist' }],
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'production_config',
            group: 'config',
            title: '拍摄配置',
            type: 'object',
            fields: [
                {
                    name: 'selected_wardrobe',
                    title: '指定服装',
                    type: 'reference',
                    to: [{ type: 'wardrobe' }],
                    // 🛡️ Critical Fix: GROQ Filter - Only show artist's available wardrobes
                    options: {
                        filter: ({ document }: { document: any }) => {
                            if (!document?.artist?._ref) {
                                return { filter: 'true' } // Show all if no artist selected
                            }
                            return {
                                filter: '_id in *[_type == "artist" && _id == $artistId].available_wardrobes[]._ref',
                                params: { artistId: document.artist._ref }
                            }
                        }
                    }
                },
                // Studio selection removed (inferred from Artist)
            ]
        },

        // === Phase 10: Perception Layer (情报源数据) ===
        {
            name: 'created_from_source',
            group: 'config',
            title: '来源情报',
            type: 'reference',
            to: [{ type: 'source' }],
            description: '此工单由哪个情报源触发创建'
        },
        {
            name: 'source_content',
            group: 'config',
            title: '原始内容',
            type: 'text',
            rows: 5,
            description: '抓取的 Markdown/Transcript 原文'
        },
        {
            name: 'source_evidence',
            group: 'config',
            title: '视觉证据',
            type: 'image',
            options: { hotspot: true },
            description: '网页截图或视频缩略图 (用于 B-Roll)'
        },

        // === Group 2: Storyboard (核心分镜) ===
        {
            name: 'storyboard',
            group: 'storyboard',
            title: '分镜脚本',
            type: 'array',
            description: 'AI 生成后，管理员可在此拖拽排序、修改台词、上传素材覆盖',
            of: [{
                type: 'object',
                title: 'Shot (镜头)',
                fields: [
                    // 🔒 Lock mechanism - prevents AI from overwriting human edits
                    {
                        name: 'is_locked',
                        title: '🔒 锁定 (Regenerate 时保留)',
                        type: 'boolean',
                        initialValue: false,
                        description: '勾选后，驳回重生成时此镜头不会被覆盖'
                    },
                    {
                        name: 'shot_number',
                        title: '镜头号',
                        type: 'number',
                        validation: (Rule: any) => Rule.required().integer().positive()
                    },
                    {
                        name: 'duration',
                        title: '时长 (秒)',
                        type: 'number',
                        validation: (Rule: any) => Rule.required().positive()
                    },
                    {
                        name: 'type',
                        title: '镜头类型',
                        type: 'string',
                        options: {
                            list: [
                                { title: 'A-Roll (艺人口播)', value: 'a_roll' },
                                { title: 'B-Roll (空镜/插画)', value: 'b_roll' },
                                { title: 'Product (产品特写)', value: 'product' }
                            ]
                        },
                        initialValue: 'a_roll'
                    },
                    {
                        name: 'script',
                        title: '口播台词',
                        type: 'text',
                        rows: 3,
                        hidden: ({ parent }: { parent: any }) => parent?.type !== 'a_roll'
                    },
                    {
                        name: 'ai_prompt',
                        title: 'AI 视觉指令',
                        type: 'text',
                        rows: 2,
                        description: '给 Flux/Wan 的 Prompt，生成 B-Roll 或产品镜头',
                        hidden: ({ parent }: { parent: any }) => parent?.type === 'a_roll' || parent?.manual_asset
                    },
                    // 🛠️ Human Override
                    {
                        name: 'manual_asset',
                        title: '🛠️ 人工替换素材',
                        type: 'file',
                        options: {
                            accept: 'video/*,image/*'
                        },
                        description: '上传视频/图片以强制覆盖 AI 生成的内容'
                    }
                ],
                preview: {
                    select: {
                        shotNumber: 'shot_number',
                        type: 'type',
                        script: 'script',
                        locked: 'is_locked'
                    },
                    prepare({ shotNumber, type, script, locked }: { shotNumber: number; type: string; script: string; locked: boolean }) {
                        const lockIcon = locked ? '🔒' : ''
                        const typeMap: Record<string, string> = {
                            a_roll: '🎤 A-Roll',
                            b_roll: '🎬 B-Roll',
                            product: '📦 Product'
                        }
                        return {
                            title: `${lockIcon} Shot ${shotNumber}: ${typeMap[type] || type}`,
                            subtitle: script?.substring(0, 50) || '(无台词)'
                        }
                    }
                }
            }]
        },

        // === Group 3: Status & Feedback ===
        {
            name: 'status',
            group: 'meta',
            title: '工单状态',
            type: 'string',
            options: {
                list: [
                    { title: '📝 Draft (AI写稿中)', value: 'draft' },
                    { title: '👀 Review (待人工审片)', value: 'review' },
                    { title: '🔙 Rejected (驳回重修)', value: 'rejected' },
                    { title: '⚙️ Rendering (生产中)', value: 'rendering' },
                    { title: '✅ Done (完成)', value: 'done' }
                ],
                layout: 'radio'
            },
            initialValue: 'draft'
        },
        {
            name: 'feedback',
            group: 'meta',
            title: '修改意见',
            type: 'text',
            rows: 3,
            hidden: ({ document }: { document: any }) => document?.status !== 'rejected',
            description: '填写意见后将状态改为 Rejected，AI 将重写未锁定的镜头。'
        },
        // Local render output (don't upload to Sanity)
        {
            name: 'local_render_path',
            group: 'meta',
            title: '本地渲染路径',
            type: 'string',
            readOnly: true,
            description: '渲染完成后的本地文件路径（由系统自动填写）'
        },
        {
            name: 'created_from_schedule',
            group: 'meta',
            title: '来源排期',
            type: 'reference',
            to: [{ type: 'schedule' }],
            readOnly: true
        }
    ],
    preview: {
        select: {
            title: 'title',
            artistName: 'artist.name',
            status: 'status'
        },
        prepare({ title, artistName, status }: { title: string; artistName: string; status: string }) {
            const statusMap: Record<string, string> = {
                draft: '📝',
                review: '👀',
                rejected: '🔙',
                rendering: '⚙️',
                done: '✅'
            }
            return {
                title: `${statusMap[status] || ''} ${title}`,
                subtitle: artistName
            }
        }
    }
}
