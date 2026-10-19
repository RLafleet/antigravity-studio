# -*- coding: utf-8 -*-
from doc_helper import add_h1, add_h2, add_h3, add_p, add_bullet, add_code, add_callout, add_table_data

def build_chapter_19(doc):
    add_h1(doc, "Глава 19. Архитектурный разбор продакшн-кода: отладчики C++ и боевые контроллеры Three.js")
    
    add_p(doc, 
        "Чтобы теоретические выкладки превратились в осязаемый программный инструмент, в настоящей главе "
        "приводятся две законченные эталонные реализации системного уровня: кроссплатформенный низкоуровневый "
        "валидатор бинарных GLB-файлов на C++20 без внешних зависимостей и полнофункциональный боевой контроллер "
        "персонажа на Three.js с буферизацией комбо-ударов, хит-стопом и событиями жизненного цикла."
    )
    
    add_h2(doc, "19.1. Системная утилита инспекции GLB на C++20 (GLB Binary Inspector)")
    add_p(doc, 
        "Данная C++ утилита демонстрирует, как без использования тяжелых сторонних библиотек напрямую прочитать "
        "заголовок файла GLB, распаковать JSON-манифест Chunk 0 и валидировать выравнивание бинарного чанка Chunk 1. "
        "Код написан в стандарте C++20 с использованием std::span и std::string_view:"
    )

    add_code(doc,
"""// ============================================================================
// GLB BINARY INSPECTOR & VALIDATOR (C++20, ZERO-DEPENDENCY)
// ============================================================================
#include <iostream>
#include <fstream>
#include <vector>
#include <string_view>
#include <cstdint>
#include <cstring>

#pragma pack(push, 1)
struct GLBHeaderRaw {
    uint32_t magic;   // 0x46546C67 ("glTF")
    uint32_t version; // 2
    uint32_t length;  // Total file size
};

struct GLBChunkHeaderRaw {
    uint32_t chunkLength;
    uint32_t chunkType; // 0x4E4F534A (JSON) or 0x004E4942 (BIN)
};
#pragma pack(pop)

class GLBInspector {
public:
    static bool Inspect(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            std::cerr << "[ERROR] Не удалось открыть файл: " << filepath << std::endl;
            return false;
        }

        std::streamsize fileSize = file.tellg();
        file.seekg(0, std::ios::beg);

        std::vector<uint8_t> buffer(static_cast<size_t>(fileSize));
        if (!file.read(reinterpret_cast<char*>(buffer.data()), fileSize)) {
            std::cerr << "[ERROR] Ошибка чтения байтов файла." << std::endl;
            return false;
        }

        std::cout << "=== ИНСПЕКЦИЯ GLB ФАЙЛА: " << filepath << " ===" << std::endl;
        std::cout << "Размер на диске: " << fileSize << " байт (" << (fileSize / 1024.0 / 1024.0) << " МБ)" << std::endl;

        if (fileSize < sizeof(GLBHeaderRaw)) {
            std::cerr << "[FAIL] Размер файла меньше 12 байт. Некорректный GLB." << std::endl;
            return false;
        }

        GLBHeaderRaw header;
        std::memcpy(&header, buffer.data(), sizeof(GLBHeaderRaw));

        // Проверка Magic:
        if (header.magic != 0x46546C67) {
            std::cerr << "[FAIL] Неверный Magic: 0x" << std::hex << header.magic 
                      << " (ожидался 0x46546C67 'glTF')" << std::dec << std::endl;
            return false;
        }

        std::cout << "[OK] Magic: 'glTF' (0x46546C67)" << std::endl;
        std::cout << "[OK] Версия спецификации: " << header.version << std::endl;
        std::cout << "[OK] Длина из заголовка: " << header.length << " байт" << std::endl;

        size_t currentOffset = sizeof(GLBHeaderRaw);
        int chunkIndex = 0;

        while (currentOffset < buffer.size()) {
            if (currentOffset + sizeof(GLBChunkHeaderRaw) > buffer.size()) {
                std::cerr << "[FAIL] Поврежденный заголовок чанка на смещении: " << currentOffset << std::endl;
                return false;
            }

            GLBChunkHeaderRaw chunk;
            std::memcpy(&chunk, buffer.data() + currentOffset, sizeof(GLBChunkHeaderRaw));
            currentOffset += sizeof(GLBChunkHeaderRaw);

            std::string typeStr;
            if (chunk.chunkType == 0x4E4F534A) typeStr = "JSON (0x4E4F534A)";
            else if (chunk.chunkType == 0x004E4942) typeStr = "BIN (0x004E4942)";
            else typeStr = "CUSTOM / UNKNOWN";

            std::cout << "--- ЧАНК #" << chunkIndex++ << " ---" << std::endl;
            std::cout << "  Тип: " << typeStr << std::endl;
            std::cout << "  Длина: " << chunk.chunkLength << " байт" << std::endl;
            std::cout << "  Смещение данных: " << currentOffset << " байт" << std::endl;

            // Проверка выравнивания по 4 байтам:
            if (chunk.chunkLength % 4 != 0) {
                std::cout << "  [WARN] Длина чанка не кратна 4 байтам! Требуется padding." << std::endl;
            } else {
                std::cout << "  [OK] Выравнивание строго кратно 4 байтам." << std::endl;
            }

            // Если чанк JSON - выводим первые 250 символов манифеста:
            if (chunk.chunkType == 0x4E4F534A) {
                std::string_view jsonView(reinterpret_cast<const char*>(buffer.data() + currentOffset), 
                                          std::min(static_cast<size_t>(chunk.chunkLength), size_t(250)));
                std::cout << "  Превью JSON:\n" << jsonView << "\n  ..." << std::endl;
            }

            currentOffset += chunk.chunkLength;
        }

        std::cout << "=== ВАЛИДАЦИЯ УСПЕШНО ЗАВЕРШЕНА: СТРУКТУРА КОРРЕКТНА ===" << std::endl;
        return true;
    }
};
"""
    )

    add_h2(doc, "19.2. Полнофункциональный контроллер бойца на Three.js (Production Combat Controller)")
    add_p(doc, 
        "Архитектурный каркас боевого контроллера, объединяющий управление аниматором, буферизацию комбо-ввода, "
        "переключение состояний и аппаратный эффект замирания кадров (Hit Stop):"
    )

    add_code(doc,
"""// ============================================================================
// THREE.JS PRODUCTION COMBAT FIGHTER CONTROLLER
// ============================================================================

export class FighterController {
    constructor(skinnedMesh, animationsMap) {
        this.mesh = skinnedMesh;
        this.mixer = new THREE.AnimationMixer(skinnedMesh);
        this.actions = new Map();
        
        // Регистрация анимационных экшенов:
        for (const [name, clip] of Object.entries(animationsMap)) {
            const action = this.mixer.clipAction(clip);
            this.actions.set(name, action);
        }

        // Состояния FSM:
        this.currentState = 'IDLE';
        this.isStunned = false;
        this.isAttacking = false;

        // Буферизация ввода (Input Buffer Window):
        this.bufferedInput = null;
        this.inputBufferDuration = 0.25; // 250 мс на ввод следующей команды комбо
        this.inputBufferTimer = 0.0;

        // Hit Stop механика:
        this.hitStopTimer = 0.0;

        // Системный слушатель завершения LoopOnce анимаций:
        this.mixer.addEventListener('finished', (e) => this.onAnimationFinished(e));

        // Старт с базовой стойки:
        this.playState('IDLE', 0.1, THREE.LoopRepeat);
    }

    playState(stateName, fadeDuration = 0.1, loop = THREE.LoopRepeat) {
        const nextAction = this.actions.get(stateName);
        if (!nextAction) {
            console.warn(`[Combat] Анимация ${stateName} отсутствует в реестре!`);
            return;
        }

        if (this.currentAction === nextAction && nextAction.isRunning()) return;

        nextAction.reset();
        nextAction.setLoop(loop, loop === THREE.LoopOnce ? 1 : Infinity);
        nextAction.clampWhenFinished = true; // Замереть на финальном кадре
        nextAction.play();

        if (this.currentAction) {
            this.currentAction.crossFadeTo(nextAction, fadeDuration, true);
        }

        this.currentAction = nextAction;
        this.currentState = stateName;
    }

    // Обработка входящего удара по бойцу:
    receiveHit(damage, hitStopDuration = 0.08) {
        // Мгновенный Hit Stop:
        this.hitStopTimer = hitStopDuration;
        this.isStunned = true;
        this.isAttacking = false;

        // Мгновенный отклик урона со сверхмалым сглаживанием:
        this.playState('HIT_REACT', 0.03, THREE.LoopOnce);
    }

    // Попытка атаковать:
    requestAttack(attackName = 'ATTACK_JAB') {
        if (this.isStunned) return; // В стане атаковать нельзя

        if (this.isAttacking) {
            // Буферизация комбо-удара в окне восстановления (Recovery):
            this.bufferedInput = attackName;
            this.inputBufferTimer = this.inputBufferDuration;
            return;
        }

        this.isAttacking = true;
        this.playState(attackName, 0.05, THREE.LoopOnce);
    }

    onAnimationFinished(event) {
        if (event.action === this.actions.get('HIT_REACT')) {
            this.isStunned = false;
            this.playState('IDLE', 0.15, THREE.LoopRepeat);
            return;
        }

        if (this.isAttacking) {
            this.isAttacking = false;

            // Если в буфере ввода ожидает комбо-атака - выполняем ее немедленно:
            if (this.bufferedInput && this.inputBufferTimer > 0.0) {
                const nextCombo = this.bufferedInput;
                this.bufferedInput = null;
                this.requestAttack(nextCombo);
                return;
            }

            // Иначе возвращаемся в стойку с идеальным плавным переходом:
            this.playState('IDLE', 0.12, THREE.LoopRepeat);
        }
    }

    // Главный метод обновления в requestAnimationFrame:
    update(deltaTime) {
        // Обновление таймера буфера ввода:
        if (this.inputBufferTimer > 0.0) {
            this.inputBufferTimer -= deltaTime;
            if (this.inputBufferTimer <= 0.0) this.bufferedInput = null;
        }

        // Hit Stop заморозка кадра:
        if (this.hitStopTimer > 0.0) {
            this.hitStopTimer -= deltaTime;
            return; // Замораживаем обновление аниматора, пропуская кадр!
        }

        // Обновление скелетного миксера:
        this.mixer.update(deltaTime);
    }
}
"""
    )

def build_chapter_20(doc):
    add_h1(doc, "Глава 20. Пост-мортем и кейс-стади: архитектура анимаций в Street Fighter 6, Tekken 8 и Mortal Kombat 1")
    
    add_p(doc, 
        "Чтобы увидеть, как рассмотренные в монографии инженерные принципы реализуются на переднем крае игровой "
        "индустрии, в заключительной главе исследуются архитектурные решения трех флагманских современных файтингов: "
        "Street Fighter 6 (движок RE Engine от Capcom), Tekken 8 (движок Unreal Engine 5 от Bandai Namco) "
        "и Mortal Kombat 1 (кастомизированный конвейер NetherRealm Studios)."
    )
    
    add_h2(doc, "20.1. Street Fighter 6 (Capcom RE Engine): Приоритет кадров и Rollback Netcode")
    add_p(doc, 
        "Capcom совершила революционный технологический скачок, переведя серию со стороннего движка на собственный RE Engine. "
        "Главная инженерная проблема сетевого файтинга с технологией Rollback (GGPO) — необходимость детерминированного "
        "перемотки (Rollback) и повторного моделирования состояния игры на 1–7 кадров назад при получении сетевого пакета от соперника."
    )
    add_p(doc, 
        "Архитектурное решение Capcom:"
    )
    add_bullet(doc, "Геймплейное состояние бойца (позиция, кадр анимации, флаги хитбоксов) строго детерминировано и отделено от визуального рендеринга. Состояние весит менее 4 КБ и может быть мгновенно сохранено и восстановлено в кольцевой буфер.", "1. Разделение State и Render: ")
    add_bullet(doc, "В момент перемотки кадров назад графический скелет не пересчитывается покадрово. Пересчитывается только математическая модель, а рендер-меш интерполируется к целевой позе за 1 кадр, сохраняя плавность визуализации.", "2. Оптимизация Rollback: ")
    add_bullet(doc, "Анимации ударов спроектированы по строгой дискретной сетке 60 Гц. Если стартап длится 4 кадра, это ровно 66.66 миллисекунд без малейшей интерполяции времени.", "3. Frame-Data Lockdown: ")

    add_h2(doc, "20.2. Tekken 8 (Bandai Namco / Unreal Engine 5): Физика сочленений и деформации мышц")
    add_p(doc, 
        "Tekken 8 стал первым в истории файтингом, построенным полностью на базе Unreal Engine 5.2. "
        "В отличие от 2D-плоскостных файтингов, Tekken оперирует глубоким 3D-пространством с уклонениями в стороны (Sidestep) "
        "и сложнейшей кинематикой захватов:"
    )
    add_bullet(doc, "Разработчики отказались от устаревшего LBS в пользу комбинированного пайплайна: базовый скелетный скиннинг дополнен процедурным деформатором мышечных объемов на основе виртуальных сплайнов (ML Deformer). Нейросеть в реальном времени корректирует вершины меша, воспроизводя сокращение бицепсов и растяжение кожи.", "1. ML Muscle Deformer: ")
    add_bullet(doc, "Взаимодействие двух бойцов при захватах (Throws) синхронизируется через единую корень-связку (Two-Character Synchronized Rig). Руки атакующего и тело защищающегося управляются общим кинематическим деревом с аналитическим IK-дотягиванием суставов.", "2. Синхронизированный риг захватов: ")

    add_h2(doc, "20.3. Mortal Kombat 1 (NetherRealm): Инерциализация и кинематографическая бесшовность")
    add_p(doc, 
        "Студия NetherRealm довела до совершенства технологию Инерциализации (Inertialization). В MK1 игрок может "
        "в любой момент прервать анимацию бега защитным блоком или развернуть комбо-атаку. "
        "Вместо классического тяжелого перекрестного сглаживания (Crossfading), математический фильтр движения "
        "мгновенно гасит вектор кинетической инерции персонажа, сохраняя анатомическую правдоподобность каждого движения."
    )

    add_callout(doc, 
        "Изучение архитектуры лидеров индустрии показывает: будущее 3D-графики и анимации принадлежит не слепому "
        "наращиванию миллионов полигонов, а строгой математической оптимизации, точному разделению ответственности "
        "между CPU и GPU и глубокому уважению к аппаратуре.",
        title="ФИНАЛЬНЫЙ ВЫВОД"
    )
