// Schema: Schedule (档期安排)
// Supports both Routine (recurring) and One-off (突发) scheduling
// ⚠️ Critical Fix: Visual config instead of Cron strings (防呆设计)
// ⚠️ Critical Fix: n8n uses 5-minute polling, not dynamic Cron

export default {
    name: 'schedule',
    title: '📅 档期安排',
    type: 'document',
    fields: [
        {
            name: 'title',
            title: '任务代号',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'artist',
            title: '执行艺人',
            type: 'reference',
            to: [{ type: 'artist' }],
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'active',
            title: '🟢 启用状态',
            type: 'boolean',
            initialValue: true
        },

        // === Type Selection ===
        {
            name: 'type',
            title: '排期类型',
            type: 'string',
            options: {
                list: [
                    { title: '🔄 常规轮播 (Routine)', value: 'routine' },
                    { title: '⚡️ 突发插播 (One-off)', value: 'one_off' }
                ],
                layout: 'radio'
            },
            initialValue: 'routine'
        },

        // === Routine Config (Visual Selection - No Cron!) ===
        {
            name: 'routine_config',
            title: '常规排期配置',
            type: 'object',
            hidden: ({ parent }: { parent: any }) => parent?.type !== 'routine',
            fields: [
                {
                    name: 'period',
                    title: '📅 周期模式',
                    type: 'string',
                    options: {
                        list: [
                            { title: '按周重复 (Weekly)', value: 'weekly' },
                            { title: '按月重复 (Monthly)', value: 'monthly' }
                        ],
                        layout: 'radio',
                        direction: 'horizontal'
                    },
                    initialValue: 'weekly'
                },
                {
                    name: 'days',
                    title: '执行星期 (Weekly)',
                    type: 'array',
                    hidden: ({ parent }: { parent: any }) => parent?.period !== 'weekly',
                    description: '请勾选需要执行的星期',
                    of: [{ type: 'string' }],
                    options: {
                        list: [
                            { title: '周一 (Mon)', value: 'monday' },
                            { title: '周二 (Tue)', value: 'tuesday' },
                            { title: '周三 (Wed)', value: 'wednesday' },
                            { title: '周四 (Thu)', value: 'thursday' },
                            { title: '周五 (Fri)', value: 'friday' },
                            { title: '周六 (Sat)', value: 'saturday' },
                            { title: '周日 (Sun)', value: 'sunday' }
                        ],
                        layout: 'grid'
                    }
                },
                {
                    name: 'month_days',
                    title: '📆 执行日期 (Monthly)',
                    type: 'array',
                    hidden: ({ parent }: { parent: any }) => parent?.period !== 'monthly',
                    description: '请输入日期号数（1-31），按回车添加',
                    of: [{
                        type: 'number',
                        validation: (Rule: any) => Rule.min(1).max(31).integer()
                    }],
                    options: { layout: 'tags' }
                },
                {
                    name: 'times',
                    title: '⏰ 执行时间 (24h)',
                    type: 'array',
                    description: '输入时间后按回车添加 (例: 09:00, 20:30)',
                    of: [{
                        type: 'string',
                        validation: (Rule: any) => Rule.regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).error('格式错: HH:mm')
                    }],
                    options: {
                        // layout: 'tags' // Removed to show validation errors clearly
                    },
                    validation: (Rule: any) => Rule.custom((times: string[]) => {
                        if (!times || times.length === 0) return '请至少添加一个时间点'
                        const invalidTimes = times.filter(t => !/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/.test(t))
                        if (invalidTimes.length > 0) return `时间格式错误: ${invalidTimes.join(', ')} (应为 HH:mm)`
                        return true
                    })
                }
            ]
        },

        // === One-off Config ===
        {
            name: 'trigger_at',
            title: '触发时间',
            type: 'datetime',
            hidden: ({ parent }: { parent: any }) => parent?.type !== 'one_off',
            validation: (Rule: any) => Rule.custom((value: string, context: any) => {
                if (context.parent?.type === 'one_off' && !value) {
                    return '突发任务必须指定触发时间'
                }
                return true
            })
        },

        // === Source Override ===
        {
            name: 'source_override',
            title: '指定监听源 (仅本次)',
            type: 'array',
            of: [{
                type: 'reference',
                to: [{ type: 'source' }],
                options: {
                    disableNew: true // 禁止在这里新建源，强制去 Source 库选
                }
            }],
            description: '留空则使用艺人默认源。填了则强制覆盖（例如突发新闻）。'
        },

        // === Execution Tracking ===
        {
            name: 'last_executed',
            title: '上次执行时间',
            type: 'datetime',
            readOnly: true,
            description: '由系统自动更新'
        }
    ],
    preview: {
        select: {
            title: 'title',
            artistName: 'artist.name',
            active: 'active',
            type: 'type'
        },
        prepare({ title, artistName, active, type }: { title: string; artistName: string; active: boolean; type: string }) {
            const statusIcon = active ? '🟢' : '🔴'
            const typeIcon = type === 'routine' ? '🔄' : '⚡️'
            return {
                title: `${statusIcon} ${title}`,
                subtitle: `${artistName} | ${typeIcon} ${type === 'routine' ? '常规' : '突发'}`
            }
        }
    }
}
