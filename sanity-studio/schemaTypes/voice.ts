// Schema: Voice (音色库)
// Base asset for CosyVoice integration

export default {
    name: 'voice',
    title: '🎤 音色库',
    type: 'document',
    fields: [
        {
            name: 'name',
            title: '音色名称',
            type: 'string',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'cosyvoice_id',
            title: 'CosyVoice 音色 ID',
            type: 'string',
            description: '用于 API 调用的标识符',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'sample_audio',
            title: '试听样本',
            type: 'file',
            options: {
                accept: 'audio/*'
            }
        },
        {
            name: 'gender',
            title: '性别',
            type: 'string',
            options: {
                list: [
                    { title: '男', value: 'male' },
                    { title: '女', value: 'female' },
                    { title: '中性', value: 'neutral' }
                ]
            }
        },
        {
            name: 'style',
            title: '风格',
            type: 'string',
            options: {
                list: [
                    { title: '专业', value: 'professional' },
                    { title: '亲切', value: 'friendly' },
                    { title: '激情', value: 'passionate' },
                    { title: '沉稳', value: 'calm' }
                ]
            }
        }
    ],
    preview: {
        select: {
            title: 'name',
            subtitle: 'style'
        }
    }
}
