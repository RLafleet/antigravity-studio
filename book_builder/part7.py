# -*- coding: utf-8 -*-
from doc_helper import add_h1, add_h2, add_h3, add_p, add_bullet, add_code, add_callout, add_table_data

def build_chapter_13(doc):
    add_h1(doc, "Глава 13. Полнофункциональная C++20 архитектура скелетного аниматора и парсера glTF")
    
    add_p(doc, 
        "Для инженера с опытом системного программирования на C++ понимание графических библиотек высокого уровня "
        "(таких как Three.js или Babylon.js) неразрывно связано с пониманием того, как те же самые алгоритмы реализуются "
        "на «чистом железе» с использованием современного стандарта C++20, многопоточности и низкоуровневых графических API "
        "(Vulkan, DirectX 12, Metal). В настоящей главе детально рассматривается промышленная архитектура скелетного "
        "анимационного движка, построенная на принципах Data-Oriented Design (DOD)."
    )
    
    add_h2(doc, "13.1. Парадигма Data-Oriented Design: почему ООП проигрывает в анимационных системах")
    add_p(doc, 
        "Традиционный объектно-ориентированный подход (OOP) представляет скелет как иерархическое дерево объектов: "
        "класс Bone содержит указатели на дочерние кости std::vector<Bone*>, матрицу трансформации, имя и кватернион вращения. "
        "При вычислении анимации процессор вынужден рекурсивно обходить дерево, «прыгая» по случайным адресам оперативной памяти. "
        "Каждый такой переход вызывает промах кэш-памяти L1/L2 (Cache Miss), простаивание конвейера инструкций процессора (CPU Stall) "
        "на 100–300 тактов и разрушает предсказатель переходов (Branch Predictor)."
    )
    add_p(doc, 
        "Современные высокопроизводительные движки (Unreal Engine 5 Chaos, Unity DOTS, Frostbite) используют парадигму "
        "Structure of Arrays (SoA) и непрерывные линейные буферы памяти (Flat Linear Arrays). В такой архитектуре все кости "
        "скелета хранятся в топологически отсортированном порядке, где индекс родительской кости ВСЕГДА строго меньше индекса дочерней (parent_index < child_index)."
    )

    add_code(doc,
"""// ============================================================================
// DATA-ORIENTED ДИЗАЙН СКЕЛЕТА (C++20 / SIMD ALIGNED)
// ============================================================================
#include <vector>
#include <string>
#include <cstdint>
#include <immintrin.h> // Intel AVX / SSE интринсики

// Выравнивание по границе 64 байт (длина кэш-линии процессора x86-64):
alignas(64) struct SkeletonData {
    uint32_t boneCount = 0;

    // Топологический массив индексов родителей (Parent Indices):
    // У корневой кости (Root) parentIndex = UINT32_MAX.
    // Гарантия топологии: parentIndices[i] < i для любого i > 0!
    std::vector<uint32_t> parentIndices;

    // Локальные трансформации костей (Local Transforms):
    std::vector<DirectX::XMFLOAT3> localPositions;
    std::vector<DirectX::XMFLOAT4> localRotations; // Кватернионы (X, Y, Z, W)
    std::vector<DirectX::XMFLOAT3> localScales;

    // Матрицы инверсной привязки (Inverse Bind Matrices):
    std::vector<DirectX::XMMATRIX> inverseBindMatrices;

    // Результирующие глобальные матрицы для загрузки в GPU VRAM:
    std::vector<DirectX::XMMATRIX> skinningPaletteMatrices;

    std::vector<std::string> boneNames;
};
"""
    )

    add_h2(doc, "13.2. Линейный расчет мировой иерархии костей без рекурсии")
    add_p(doc, 
        "Благодаря гарантии топологической сортировки (индекс родителя всегда меньше индекса ребенка), вычисление мировой "
        "трансформации всех 60 костей скелета сводится к тривиальному линейному циклу for от 0 до N, который великолепно "
        "векторизуется компилятором (SIMD Auto-Vectorization) и исполняется на регистрах процессора с нулевыми промахами кэша:"
    )

    add_code(doc,
"""// Линейное обновление матриц скелета со 100% локальностью кэша:
void UpdateSkeletonTransforms(SkeletonData& skeleton) {
    const uint32_t count = skeleton.boneCount;

    // Временный вектор мировых матриц:
    std::vector<DirectX::XMMATRIX> worldMatrices(count);

    for (uint32_t i = 0; i < count; ++i) {
        // 1. Построение локальной аффинной матрицы кости M_local = S * R * T:
        DirectX::XMVECTOR scale = DirectX::XMLoadFloat3(&skeleton.localScales[i]);
        DirectX::XMVECTOR rot = DirectX::XMLoadFloat4(&skeleton.localRotations[i]);
        DirectX::XMVECTOR trans = DirectX::XMLoadFloat3(&skeleton.localPositions[i]);

        DirectX::XMMATRIX localMatrix = 
            DirectX::XMMatrixScalingFromVector(scale) *
            DirectX::XMMatrixRotationQuaternion(rot) *
            DirectX::XMMatrixTranslationFromVector(trans);

        // 2. Умножение на матрицу родителя:
        uint32_t parent = skeleton.parentIndices[i];
        if (parent == UINT32_MAX) {
            // Корневая кость (Root Bone): мировая матрица равна локальной
            worldMatrices[i] = localMatrix;
        } else {
            // Дочерняя кость: родительская матрица УЖЕ вычислена на предыдущих шагах цикла!
            // Никакой рекурсии, мгновенное чтение из кэша L1!
            worldMatrices[i] = localMatrix * worldMatrices[parent];
        }

        // 3. Вычисление финальной матрицы скиннинга для вершинного шейдера:
        // M_skin = M_inv_bind * M_world
        skeleton.skinningPaletteMatrices[i] = 
            skeleton.inverseBindMatrices[i] * worldMatrices[i];
    }
}
"""
    )

    add_h2(doc, "13.3. Высокопроизводительная интерполяция анимационных каналов")
    add_p(doc, 
        "Анимационный клип в glTF состоит из набора каналов (Channels) и сэмплеров (Samplers). "
        "Каждый сэмплер хранит массив временных меток keyframeTimes[K] и массив значений keyframeValues[K] "
        "(позиций, кватернионов или масштабов). Чтобы найти позу скелета в произвольный момент времени t, "
        "необходимо найти два соседних ключевых кадра [k, k+1] и вычислить коэффициент интерполяции alpha:"
    )

    add_code(doc,
"""// Поиск ключевых кадров бинарным поиском и расчет коэффициента alpha:
struct AnimationSampler {
    std::vector<float> timestamps;
    std::vector<DirectX::XMFLOAT4> quaternionKeyframes;

    DirectX::XMVECTOR EvaluateQuaternion(float currentTime) const {
        if (timestamps.empty()) return DirectX::XMQuaternionIdentity();
        if (currentTime <= timestamps.front()) return DirectX::XMLoadFloat4(&quaternionKeyframes.front());
        if (currentTime >= timestamps.back())  return DirectX::XMLoadFloat4(&quaternionKeyframes.back());

        // Бинарный поиск ближайшего кадра (O(log K)):
        auto it = std::lower_bound(timestamps.begin(), timestamps.end(), currentTime);
        size_t index1 = std::distance(timestamps.begin(), it);
        size_t index0 = index1 - 1;

        float t0 = timestamps[index0];
        float t1 = timestamps[index1];
        float alpha = (currentTime - t0) / (t1 - t0);

        // Загрузка кватернионов в 128-битные SIMD регистры:
        DirectX::XMVECTOR q0 = DirectX::XMLoadFloat4(&quaternionKeyframes[index0]);
        DirectX::XMVECTOR q1 = DirectX::XMLoadFloat4(&quaternionKeyframes[index1]);

        // Сферическая интерполяция кватернионов (SLERP):
        return DirectX::XMQuaternionSlerp(q0, q1, alpha);
    }
};
"""
    )

    add_h2(doc, "13.4. Передача матриц на GPU: UBO против SSBO и Bone Texture")
    add_p(doc, 
        "Когда матрицы скиннинга вычислены, их необходимо передать на графический процессор. Существуют три стратегии передачи:"
    )
    table_gpu_headers = ["Метод передачи данных", "API и стандарты", "Макс. размер данных", "Плюсы и архитектурные минусы"]
    table_gpu_data = [
        ["Uniform Buffer Object (UBO)", "OpenGL 3.3+, Vulkan, D3D11", "Обычно 64 КБ (хватает на ~250 матриц)", "Самая быстрая выборка на GPU (Uniform Cache); ограничено по размеру."],
        ["Shader Storage Buffer (SSBO)", "OpenGL 4.3+, Vulkan, WebGPU", "До 128 МБ - 2 ГБ", "Неограниченное число костей и инстансов; чуть медленнее UBO на мобильных чипах."],
        ["Float Data Texture (RGBA32F)", "WebGL 1.0/2.0, OpenGLES 3.0", "Разрешение текстуры (4096 x 4096)", "Универсально поддерживается в любом мобильном веб-браузере; выборка через texelFetch."]
    ]
    add_table_data(doc, table_gpu_headers, table_gpu_data)

def build_chapter_14(doc):
    add_h1(doc, "Глава 14. Физически корректный рендеринг (PBR) и микрогранная теория в деталях")
    
    add_p(doc, 
        "Стандарт Physically Based Rendering (PBR), положенный в основу современных шейдеров Three.js (MeshStandardMaterial / MeshPhysicalMaterial), "
        "Unreal Engine и Blender Cycles/EEVEE, представляет собой строгую математическую модель взаимодействия электромагнитного излучения (света) "
        "с границей раздела двух диэлектрических или проводящих сред. В настоящей главе рассматривается микрогранная теория Кука-Торренса "
        "и математика двулучевой функции распределения отражения (BRDF)."
    )
    
    add_h2(doc, "14.1. Уравнение рендеринга и интеграл освещенности")
    add_p(doc, 
        "Фундаментальное уравнение рендеринга (Rendering Equation), сформулированное Джеймсом Каджией в 1986 году, "
        "определяет суммарную спектральную яркость излучения L_o, исходящего из точки поверхности p в направлении наблюдателя v:"
    )

    add_code(doc,
"""// Уравнение рендеринга Каджии:
// L_o(p, v) = L_e(p, v) + INTEGRAL_Omega [ f_r(p, l, v) * L_i(p, l) * (n * l) * d_omega ]
//
// Где:
// L_o(p, v)     - Итоговый свет, летящий в камеру
// L_e(p, v)     - Собственное свечение поверхности (Emissive)
// INTEGRAL_Omega- Интеграл по всей полусфере над точкой поверхности
// f_r(p, l, v)  - Двулучевая функция распределения отражения (BRDF)
// L_i(p, l)     - Входящий свет из направления l
// (n * l)       - Косинус угла падения (закон Ламберта, скалярное произведение)
// d_omega       - Дифференциал телесного угла
"""
    )

    add_h2(doc, "14.2. Модель микрограней Кука-Торренса (Cook-Torrance Specular BRDF)")
    add_p(doc, 
        "Модель Кука-Торренса разделяет падающий свет на две составляющие: диффузную (преломленный свет, рассеянный внутри материала) "
        "и зеркальную (свет, отраженный непосредственно от поверхности):"
    )
    add_code(doc,
"""// Разделение BRDF на диффузную и спекулярную составляющие:
// f_r(l, v) = k_d * f_diffuse + k_s * f_specular
// При этом закон сохранения энергии требует: k_d + k_s <= 1.0 (для диэлектриков).
// Для чистых металлов (Metallic = 1.0): k_d = 0.0 (металлы полностью поглощают преломленный свет).
"""
    )
    add_p(doc, 
        "Зеркальная составляющая Cook-Torrance Specular BRDF вычисляется по формуле трех сомножителей:"
    )
    add_code(doc,
"""// Формула Cook-Torrance Specular BRDF:
//                    D(h) * F(v, h) * G(l, v, h)
// f_specular(l, v) = ---------------------------
//                        4 * (n * l) * (n * v)
//
// Где:
// h = normalize(l + v) - Вектор полупути (Halfway Vector)
// D(h)       - Функция распределения нормалей микрограней (Normal Distribution Function - NDF)
// F(v, h)    - Функция Френеля (Fresnel Reflectance)
// G(l, v, h) - Геометрическая функция самозатенения микрограней (Geometric Shadowing/Masking)
"""
    )

    add_h3(doc, "1. Функция распределения нормалей D(h): GGX / Trowbridge-Reitz")
    add_p(doc, 
        "Функция D(h) моделирует статистическое распределение микроскопических граней поверхности, чьи локальные нормали "
        "ориентированы строго вдоль вектора полупути h. В индустрии стандартом де-факто является распределение GGX (Trowbridge-Reitz):"
    )
    add_code(doc,
"""// Реализация функции GGX NDF в GLSL:
float DistributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness; // Переход в перцептивно-линейное пространство
    float a2 = a * a;
    float NdotH = max(dot(N, H), 0.0);
    float NdotH2 = NdotH * NdotH;

    float denom = (NdotH2 * (a2 - 1.0) + 1.0);
    denom = 3.14159265359 * denom * denom;

    return a2 / max(denom, 0.0000001);
}
"""
    )

    add_h3(doc, "2. Уравнение Френеля F(v, h): Аппроксимация Шлика (Fresnel-Schlick)")
    add_p(doc, 
        "Закон Френеля описывает физический феномен: под скользящими углами взгляда любая поверхность (даже матовая резина или асфальт) "
        "становится почти идеальным зеркалом (отражение стремится к 100%). Для вычислений реального времени используется "
        "аналитическая аппроксимация Шлика:"
    )
    add_code(doc,
"""// Аппроксимация Френеля-Шлика в GLSL:
vec3 FresnelSchlick(float cosTheta, vec3 F0) {
    // F0 - базовое отражение при перпендикулярном взгляде (0.04 для пластика/кожи, Albedo для металлов)
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}
"""
    )

    add_h3(doc, "3. Геометрическая функция самозатенения G(l, v, h): Smith-Schlick GGX")
    add_p(doc, 
        "Функция G учитывает вероятность того, что отраженный микрогранью луч света будет заблокирован соседней микрогранью "
        "(Masking) или затенен ею от источника света (Shadowing). Метод Смита разделяет функцию на два независимых направления:"
    )
    add_code(doc,
"""// Геометрическое затенение Смита-Шлика в GLSL:
float GeometrySchlickGGX(float NdotV, float roughness) {
    float r = (roughness + 1.0);
    float k = (r * r) / 8.0; // Для прямого освещения (Direct Lighting)

    float denom = NdotV * (1.0 - k) + k;
    return NdotV / max(denom, 0.0000001);
}

float GeometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float NdotV = max(dot(N, V), 0.0);
    float NdotL = max(dot(N, L), 0.0);
    float ggx2 = GeometrySchlickGGX(NdotV, roughness);
    float ggx1 = GeometrySchlickGGX(NdotL, roughness);

    return ggx1 * ggx2;
}
"""
    )

    add_h2(doc, "14.3. Освещение на основе окружения (Image-Based Lighting - IBL)")
    add_p(doc, 
        "В реальном мире персонаж освещается не одним точечным источником, а всем окружающим куполом атмосферы и интерьера. "
        "Вычисление интеграла освещенности от сотен тысяч направлений кубической карты (Cubemap) в реальном времени невозможно. "
        "Поэтому Брайан Карис (Epic Games) разработал метод Split-Sum Approximation:"
    )
    add_bullet(doc, "Окружающая среда предварительно размывается по полусфере с косинусным взвешиванием и запекается в низкополигональную кубическую карту Irradiance Map. Диффузное освещение вычисляется одной выборкой texture(uIrradianceMap, N).", "1. Диффузная часть (Irradiance): ")
    add_bullet(doc, "Карта окружения размывается фильтром GGX для разных уровней шероховатости (Roughness от 0.0 до 1.0) и записывается в мип-уровни кубической карты (Prefiltered Environment Map). Спекулярная выборка выполняется через textureLod(uPrefilteredEnv, R, roughness * maxMipLevel).", "2. Зеркальная часть (Prefiltered Specular): ")
    add_bullet(doc, "Интеграл Френеля и геометрии запекается в двумерную статическую текстуру поиска (BRDF Integration LUT), которая связывает угол NdotV и шероховатость с весовыми коэффициентами отражения.", "3. Таблица отклика (BRDF LUT): ")

    add_callout(doc, 
        "Именно благодаря Split-Sum IBL персонаж в Three.js при включении PMREMGenerator выглядит материальным, "
        "органично вписанным в сцену, а не парящим пластиковым объектом.",
        title="СЕКРЕТ РЕАЛИЗМА IBL"
    )
