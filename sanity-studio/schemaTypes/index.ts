// Schema Index - Export all schema types
// Order matters: base assets first, then entities that reference them

import voice from './voice'
import source from './source'
import wardrobe from './wardrobe'
import artist from './artist'
import schedule from './schedule'
import post from './post'
import prompt_config from './prompt_config'

export const schemaTypes = [
    // Base Assets (no dependencies)
    voice,
    source,
    wardrobe,
    prompt_config, // Brain
    // Core Entities (reference base assets)
    artist,
    // Execution Layer (reference artists)
    schedule,
    post,
]

