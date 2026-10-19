# -*- coding: utf-8 -*-
from doc_helper import add_h1, add_h2, add_h3, add_p, add_bullet, add_code, add_callout, add_table_data

def build_chapter_7(doc):
    add_h1(doc, "Глава 7. Экосистема софта и сравнительный анализ редакторов персонажей")
    
    add_p(doc, 
        "Выбор инструментария для создания персонажей — это фундаментальное архитектурное решение, определяющее "
        "себестоимость производства контента (Content Production Cost), скорость итераций и техническую совместимость с движком. "
        "Рынок разделен на два принципиальных сегмента: традиционные цифровые мастерские (Digital Content Creation — DCC) "
        "и параметрические генераторы следующего поколения."
    )
    
    add_h2(doc, "7.1. Профессиональные DCC-пакеты (Ручной пайплайн)")
    
    add_bullet(doc, "Главный открытый и полностью бесплатный 3D-комбайн планеты. Содержит полный цикл: скульптинг, ретопологию, процедурную UV-развертку, запекание, риггинг (мощнейший аддон Rigify) и нативный экспорт в glTF 2.0 / GLB. Обладает открытым Python API, позволяющим писать плагины пакетной автоматизации. Идеальный базовый инструмент для любого инди-разработчика.", "Blender 4.x (Open Source): ")
    add_bullet(doc, "Индустриальный стандарт кинематографа и AAA-геймдева для риггинга и анимации. Обладает эталонными матричными нодами трансформаций и лучшей в отрасли системой развесовки (Paint Skin Weights). Минусы: драконовская подписочная модель ($1,875 в год), отсутствие встроенных современных PBR-текстурных кистей, сложный порог входа.", "Autodesk Maya: ")
    add_bullet(doc, "Абсолютный монополист в области высокополигональной цифровой лепки. Способен оперировать сетками до 100 миллионов полигонов на обычном ПК без GPU-акселерации за счет собственного воксельного движка Pixols. Минусы: узкая специализация (в нем нельзя анимировать или собирать игровые сцены), специфический интерфейс 1990-х годов.", "Pixologic ZBrush: ")

    add_h2(doc, "7.2. Параметрические генераторы персонажей: детальный разбор")
    add_p(doc, 
        "Параметрические генераторы позволяют собирать готовых анимированных персонажей за минуты вместо недель ручного моделирования. "
        "Однако каждый из них имеет строго очерченные архитектурные границы применимости."
    )

    add_h3(doc, "7.2.1. Ready Player Me (Web / Cloud API)")
    add_p(doc, 
        "Ready Player Me — кроссплатформенная веб-система генерации аватаров. "
        "Создана специально для браузерных движков, WebGL и метаверсов."
    )
    add_bullet(doc, "Чистый Web, не требует установки. Предоставляет открытый REST API: можно передать ссылку на сгенерированного аватара `https://models.readyplayer.me/id.glb` прямо в Three.js `gltfLoader.load()`, и персонаж загрузится в реальном времени.", "Архитектура: ")
    add_bullet(doc, "Скелет на 100% соответствует стандарту Mixamo Humanoid + имеет запеченные 52 морф-таргета стандарта Apple ARKit для трекинга лица через фронтальную камеру смартфона.", "Скелет и риг: ")
    add_bullet(doc, "Сетка оптимизирована под мобильные GPU: 8,000 – 14,000 треугольников, 1 PBR-текстурный атлас (1024x1024 или 2048x2048).", "Топология: ")
    add_bullet(doc, "Стилистика сугубо антропоморфная (современные люди, бойцы, киберпанк). Сделать из него горбатого некроманта или огненного монстра невозможно.", "Ограничения: ")

    add_h3(doc, "7.2.2. VRoid Studio (Pixiv)")
    add_p(doc, 
        "Бесплатный настольный редактор от японской корпорации Pixiv, созданный для VTuber-индустрии и мобильных аниме-экшенов."
    )
    add_bullet(doc, "Параметрические слайдеры тела и лица (сотни параметров). Уникальный генератор процедурных 3D-волос (рисование прядей кривыми Безье прямо по черепу). Встроенный графический редактор для рисования текстур кожи и одежды по слоям с поддержкой прозрачности.", "Функционал: ")
    add_bullet(doc, "Экспорт в открытый стандарт VRM (надстройка над glTF 2.0). Содержит скелет Humanoid + систему пружинной физики вторичных деформаций (VRM Spring Bones для волос и ткани) + морф-таргеты эмоций (Blink, Joy, Angry, Sorrow, Fun).", "Формат: ")
    add_bullet(doc, "Стилистика аниме/полуреализм. Для темного мрачного фэнтези требует перекраски текстур.", "Ограничения: ")

    add_h3(doc, "7.2.3. Character Creator 4 (Reallusion)")
    add_p(doc, 
        "Промышленный монстр параметрической генерации для AAA-студий."
    )
    add_bullet(doc, "Фотореалистичная анатомия любого возраста, пола и расы. Превосходная генерация морщин под скиннинг (Wrinkle Maps), автоматический перенос весов при смене одежды.", "Возможности: ")
    add_bullet(doc, "Слишком тяжелая геометрия по умолчанию (40,000 – 80,000 полигонов, множество материалов и 4K-текстур). Для мобильного WebGL требует жесткой ручной децимации и объединения материалов в атласы (Draw Call Reduction). Платная лицензия ($299 – $790).", "Ограничения: ")

    add_h2(doc, "7.3. Сравнительная инженерная матрица генераторов персонажей")

    headers_gen = ["Инструмент", "Платформа", "Полигонаж (LOD0)", "Скелетный стандарт", "Морф-таргеты лица", "Применимость к WebGL / TMA"]
    rows_gen = [
        ["Ready Player Me", "Web / Cloud REST", "8,000 – 14,000", "Mixamo / ARKit (100% match)", "52 (ARKit Blendshapes)", "10/10 (Идеально из коробки)"],
        ["VRoid Studio", "Win / Mac / Steam", "12,000 – 22,000", "VRM Humanoid (glTF)", "30+ (VRM Expressions)", "9/10 (Требует three-vrm)"],
        ["Mixamo + Free Rig", "Web (Adobe Cloud)", "5,000 – 35,000", "Mixamo Standard", "Нет (Только скелет)", "10/10 (Родной стандарт Three.js)"],
        ["Character Creator 4", "Windows Desktop", "40,000 – 90,000", "CC Humanoid / Unreal", "140+ (FACS System)", "4/10 (Слишком тяжелый для TMA)"],
        ["MetaHuman", "Unreal Engine Cloud", "80,000 – 150,000", "Unreal Rig (DNA System)", "800+ (Extreme Fidelity)", "1/10 (Только для ПК/PS5)"],
        ["MakeHuman", "Open Source Desktop", "15,000 – 25,000", "Rigify / Game Engine", "Базовые фонемы", "6/10 (Устаревшая топология)"]
    ]
    add_table_data(doc, headers_gen, rows_gen)

def build_chapter_8(doc):
    add_h1(doc, "Глава 8. Рендеринг и шейдеры скиннинга в WebGL 2.0 и Three.js")
    
    add_p(doc, 
        "Когда файл GLB загружен и десериализован рантаймом в оперативную память браузера, в игру вступает графический конвейер WebGL. "
        "В этой главе мы подробно разберем, как устроен вершинный шейдер скиннинга на низком уровне и как движок Three.js "
        "обходит критические аппаратные лимиты мобильных видеокарт."
    )
    
    add_h2(doc, "8.1. Проблема лимита Uniform-векторов (MAX_VERTEX_UNIFORM_VECTORS)")
    add_p(doc, 
        "В традиционном OpenGL/DirectX костные матрицы передавались в шейдер через массив констант Uniform-буфера:"
    )
    add_code(doc, "uniform mat4 u_boneMatrices[MAX_BONES];")
    add_p(doc, 
        "Каждая матрица $4 \\times 4$ занимает ровно 4 вектора `vec4`. "
        "Для скелета персонажа из 64 костей требуется: $64 \\times 4 = 256$ векторов `vec4` только под матрицы костей! "
        "Однако спецификация WebGL на многих бюджетных мобильных чипсетах (ARM Mali-G52, Mali-T880, старые Qualcomm Adreno) "
        "гарантирует аппаратный лимит `MAX_VERTEX_UNIFORM_VECTORS` всего в **128 или 256 векторов**."
    )
    add_p(doc, 
        "Если попытаться скомпилировать такой шейдер на бюджетном смартфоне, WebGL упадет с ошибкой `Shader compile error: too many uniform vectors`. "
        "Приложение моментально крашится."
    )

    add_h2(doc, "8.2. Архитектурное решение: Костная текстура (Bone Texture / Data Texture)")
    add_p(doc, 
        "Чтобы снять ограничение на количество костей раз и навсегда, Three.js использует технику костной текстуры (Bone Texture). "
        "Вся палитра матриц костей упаковывается в плоскую текстуру данных с плавающей точкой (Float Data Texture) формата `RGBA32F`:"
    )
    add_bullet(doc, "Ширина текстуры: 4 текселя (так как матрица 4х4 состоит из четырех столбцов vec4).", "Размерность текстуры: ")
    add_bullet(doc, "Высота текстуры: равна количеству костей скелета N (например, 64 текселя).", "Высота: ")
    add_bullet(doc, "Каждый пиксель (R, G, B, A) хранит четыре 32-битных числа float (IEEE 754). Строка из 4 пикселей представляет одну полную матрицу трансформации кости 4х4.", "Формат данных: ")

    add_p(doc, 
        "В вершинном шейдере выборка матрицы $k$-й кости производится быстрой функцией `texelFetch()` (доступной в WebGL 2.0 / GLSL ES 3.0), "
        "которая обращается к текстуре напрямую по целочисленным координатам пикселей без фильтрации и билинейной интерполяции:"
    )

    add_code(doc,
"""// ============================================================================
// ВЕРШИННЫЙ ШЕЙДЕР СКИННИНГА WEBGL 2.0 (GLSL ES 3.0 / THREE.JS EQUIVALENT)
// ============================================================================
#version 300 es

// Входные вершинные атрибуты из VBO
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in vec4 a_joints;   // Индексы 4 влияющих костей (целые числа)
layout(location = 4) in vec4 a_weights;  // Веса 4 костей (сумма = 1.0)

// Матрицы камеры и проекции
uniform mat4 u_viewMatrix;
uniform mat4 u_projectionMatrix;
uniform mat4 u_modelMatrix;

// Костная текстура (Float Data Texture)
uniform sampler2D u_boneTexture;
uniform int u_boneTextureSize;

// Выходные данные для фрагментного шейдера
out vec2 v_uv;
out vec3 v_worldNormal;
out vec3 v_worldPosition;

// Функция извлечения матрицы 4х4 для кости boneIndex из текстуры
mat4 getBoneMatrix(int boneIndex) {
    // Каждая кость занимает 4 последовательных текселя в строке
    int x = (boneIndex * 4) % u_boneTextureSize;
    int y = (boneIndex * 4) / u_boneTextureSize;

    vec4 col0 = texelFetch(u_boneTexture, ivec2(x + 0, y), 0);
    vec4 col1 = texelFetch(u_boneTexture, ivec2(x + 1, y), 0);
    vec4 col2 = texelFetch(u_boneTexture, ivec2(x + 2, y), 0);
    vec4 col3 = texelFetch(u_boneTexture, ivec2(x + 3, y), 0);

    return mat4(col0, col1, col2, col3);
}

void main() {
    v_uv = a_uv;

    // 1. Извлечение 4 матриц скиннинга по индексам костей
    mat4 boneMat0 = getBoneMatrix(int(a_joints.x));
    mat4 boneMat1 = getBoneMatrix(int(a_joints.y));
    mat4 boneMat2 = getBoneMatrix(int(a_joints.z));
    mat4 boneMat3 = getBoneMatrix(int(a_joints.w));

    // 2. Linear Blend Skinning позиции вершины
    vec4 localPosition = vec4(a_position, 1.0);
    vec4 skinnedPosition = 
        (boneMat0 * localPosition) * a_weights.x +
        (boneMat1 * localPosition) * a_weights.y +
        (boneMat2 * localPosition) * a_weights.z +
        (boneMat3 * localPosition) * a_weights.w;

    // 3. Linear Blend Skinning нормали (только верхняя 3х3 часть матриц)
    vec3 skinnedNormal = 
        (mat3(boneMat0) * a_normal) * a_weights.x +
        (mat3(boneMat1) * a_normal) * a_weights.y +
        (mat3(boneMat2) * a_normal) * a_weights.z +
        (mat3(boneMat3) * a_normal) * a_weights.w;

    // 4. Финальный перенос в мировое пространство и пространство отсечения (Clip Space)
    vec4 worldPos = u_modelMatrix * skinnedPosition;
    v_worldPosition = worldPos.xyz;
    v_worldNormal = normalize(mat3(u_modelMatrix) * skinnedNormal);

    gl_Position = u_projectionMatrix * u_viewMatrix * worldPos;
}
"""
    )

    add_h2(doc, "8.3. Архитектура рантайма Three.js: SkinnedMesh, Skeleton и AnimationMixer")
    add_p(doc, 
        "На уровне высокоуровневого API Three.js скиннинг управляется связкой трех классов:"
    )
    add_bullet(doc, "Потомок `THREE.Mesh`. В отличие от обычного меша, содержит ссылку на `THREE.Skeleton` и автоматически добавляет в вершинный шейдер скиннинговые директивы `#define USE_SKINNING`.", "THREE.SkinnedMesh: ")
    add_bullet(doc, "Иерархический массив объектов `THREE.Bone` (каждый из которых наследует `THREE.Object3D`), плоский массив `boneMatrices` (Float32Array) и массив запеченных `boneInverses` (Matrix4). Метод `skeleton.update()` вызывается один раз за кадр для сбора глобальных матриц всех костей и заливки их в `boneTexture`.", "THREE.Skeleton: ")
    add_bullet(doc, "Глобальный плеер анимаций персонажа. Принимает на вход дельту времени `mixer.update(dt)`. Управляет набором действий `THREE.AnimationAction` (запуск, остановка, зацикливание, кроссфейды, веса смешивания).", "THREE.AnimationMixer: ")

    add_h2(doc, "8.4. Математика смешивания анимаций (CrossFading & Layering)")
    add_p(doc, 
        "В файтинге персонаж непрерывно переходит между состояниями: `Idle` $\\rightarrow$ `HitReact` $\\rightarrow$ `Idle` или `Attack` $\\rightarrow$ `Death`. "
        "Мгновенное переключение клипов (Hard Cut) недопустимо, так как вызывает резкий рывок костей. "
        "Для гладкого перехода применяется алгоритм плавного угасания и нарастания весов (CrossFade):"
    )
    add_code(doc,
"""// Плавный кроссфейд между клипами A и B за время T (в секундах):
actionA.fadeOut(T);
actionB.reset().fadeIn(T).play();

// В каждый момент времени t в интервале [0, T]:
weightA(t) = 1.0 - (t / T);
weightB(t) = (t / T);

// Для каждого сустава кватернионы вращения интерполируются методом SLERP:
Q_blended(t) = slerp( Q_actionA(t), Q_actionB(t), weightB(t) );
"""
    )
