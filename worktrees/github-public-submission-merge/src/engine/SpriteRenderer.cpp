#include "engine/SpriteRenderer.hpp"
#include <iostream>

namespace engine {

SpriteRenderer::SpriteRenderer() {
    renderQueue_.reserve(100);
}

void SpriteRenderer::DrawSprite(const std::string& textureId, const Vector2& position, const Vector2& size, const AABB& uv) {
    renderQueue_.push_back({textureId, position, size, uv});
}

void SpriteRenderer::Render() {
    // In a full graphics engine, this would make OpenGL/Vulkan/DirectX calls.
    // compatible with 16-bit aesthetic (pixel snapping could happen here).
    // For this headless/CLI engine, we output a structured representation 
    // that the Frontend (React/WebGL) can parse.
    
    // Minimal JSON-like output for "visual" debugging via stdout
    if (renderQueue_.empty()) return;

    std::cout << "{\"type\": \"render_frame\", \"sprites\": [";
    for (size_t i = 0; i < renderQueue_.size(); ++i) {
        const auto& s = renderQueue_[i];
        std::cout << "{\"tex\": \"" << s.textureId << "\", "
                  << "\"x\": " << s.position.x << ", \"y\": " << s.position.y << ", "
                  << "\"w\": " << s.size.x << ", \"h\": " << s.size.y 
                  << "}";
        if (i < renderQueue_.size() - 1) std::cout << ", ";
    }
    std::cout << "]}" << std::endl;

    renderQueue_.clear();
}

} // namespace engine
