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
            description: '用于 API 调用的标识符 (Zero-Shot模式可留空)'
        },
        {
            name: 'sample_audio',
            title: '参考音频',
            type: 'file',
            options: {
                accept: 'audio/*'
            },
            description: '⚠️ 必须是清晰的单人语音，3-10秒为佳',
            validation: (Rule: any) => Rule.required()
        },
        {
            name: 'sample_transcription',
            title: '参考音频文字',
            type: 'text',
            rows: 3,
            description: '⚠️ 必填！音频中说的原文内容（用于Zero-Shot克隆）',
            validation: (Rule: any) => Rule.required()
        }
    ],
    preview: {
        select: {
            title: 'name',
            subtitle: 'cosyvoice_id'
        }
    }
}
