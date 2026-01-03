// Schema Index - Export all schema types
// Order matters: base assets first, then entities that reference them

import voice from './voice'
import source from './source'
import wardrobe from './wardrobe'
import studio from './studio'
import artist from './artist'
import schedule from './schedule'
import post from './post'

export const schemaTypes = [
    // Base Assets (no dependencies)
    voice,
    source,
    wardrobe,
    studio,
    // Core Entities (reference base assets)
    artist,
    // Execution Layer (reference artists)
    schedule,
    post,
]
