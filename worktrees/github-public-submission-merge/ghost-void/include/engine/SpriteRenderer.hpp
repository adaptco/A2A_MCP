#pragma once

#include "Physics.hpp"
#include <vector>
#include <string>

namespace engine {

struct Sprite {
    std::string textureId;
    Vector2 position;
    Vector2 size;
    AABB uv; // Texture coordinates
};

class SpriteRenderer {
public:
    SpriteRenderer();
    
    // Queue a sprite for rendering this frame
    void DrawSprite(const std::string& textureId, const Vector2& position, const Vector2& size, const AABB& uv);
    
    // Flush the render queue (output 16-bit style JSON/Text representation for now)
    void Render();

private:
    std::vector<Sprite> renderQueue_;
};

} // namespace engine
