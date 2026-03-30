from __future__ import annotations

import html
import json
import os
import re
import secrets
import time
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from typing import Callable

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from sqlalchemy import create_engine, delete, func, select, text, update
from sqlalchemy.sql import and_, or_
from sqlalchemy.orm import Session, sessionmaker

from models import (
    AdminUser,
    Asset,
    Base,
    ContentBlock,
    DocumentCategory,
    User,
    SupportAttachment,
    SupportComplaintMedia,
    SupportMessage,
    SupportWorkLog,
    SupportWorkLogMedia,
    UserEventLog,
)


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "site.db"
UPLOAD_DIR = APP_DIR / "static" / "uploads"

ALLOWED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "svg", "ico"}
ALLOWED_DOC_EXTS = {"pdf", "doc", "docx", "xls", "xlsx", "zip", "rar"}
ALLOWED_SUPPORT_UPLOAD_EXTS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "bmp",
    "webp",
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "zip",
    "rar",
    "txt",
    "log",
    "csv",
    "mp3",
    "wav",
    "ogg",
    "m4a",
    "mp4",
    "mov",
    "webm",
    "avi",
}

DEFAULT_CONTENT: dict[str, dict[str, str]] = {
    "brand_full": {"title": "Бренд (полное)", "body": "СКУД «Стражъ | Авангардъ»"},
    "slogan": {"title": "Слоган", "body": "Российская сетевая СКУД для объектов любой сложности"},
    "hero_title": {"title": "Заголовок (Hero)", "body": "Сетевая СКУД «Стражъ | Авангардъ»"},
    "hero_subtitle": {
        "title": "Подзаголовок (Hero)",
        "body": "Российская система контроля и управления доступом. Надёжная защита периметра, учёт рабочего времени и интеграция с корпоративными системами.",
    },
    "hero_cta_primary": {"title": "Hero — кнопка 1", "body": "Запросить КП"},
    "hero_cta_secondary": {"title": "Hero — кнопка 2", "body": "Калькулятор"},
    "hero_mockup_label": {"title": "Hero — подпись макета", "body": "В реестре ПО РФ"},
    "hero_tag_2": {"title": "Hero — тег 2", "body": "Импортозамещение"},
    "hero_tag_3": {"title": "Hero — тег 3", "body": "Подходит для КИИ"},
    "hero_slide2_title": {"title": "Hero — слайд 2 заголовок", "body": "Импортозамещение без компромиссов"},
    "hero_slide2_subtitle": {
        "title": "Hero — слайд 2 подзаголовок",
        "body": "Готово для внедрения на объектах КИИ и в организациях с повышенными требованиями к безопасности.",
    },
    "hero_slide3_title": {"title": "Hero — слайд 3 заголовок", "body": "Единая платформа доступа и учета"},
    "hero_slide3_subtitle": {
        "title": "Hero — слайд 3 подзаголовок",
        "body": "Биометрия, Anti-passback, отчётность и интеграции — в одном решении.",
    },
    "hero_slide4_title": {"title": "Hero — слайд 4 заголовок", "body": "Быстрый запуск и масштабирование"},
    "hero_slide4_subtitle": {
        "title": "Hero — слайд 4 подзаголовок",
        "body": "От пилота до распределённой сети объектов: единые политики доступа, централизованное управление и контроль.",
    },
    "hero_slide5_title": {"title": "Hero — слайд 5 заголовок", "body": "Интеграции и отчётность"},
    "hero_slide5_subtitle": {
        "title": "Hero — слайд 5 подзаголовок",
        "body": "Готовая аналитика, экспорт данных и интеграции с корпоративными системами и оборудованием.",
    },
    "registry_title": {"title": "Реестр — заголовок", "body": "Включено в Единый реестр российских программ"},
    "registry_description": {
        "title": "Реестр — описание",
        "body": "Программный комплекс «Стражъ | Авангардъ» официально зарегистрирован в реестре Минцифры РФ. Подходит для импортозамещения на объектах КИИ и в государственных структурах.",
    },
    "registry_badge_label": {"title": "Реестр — верхняя плашка", "body": "Государственная регистрация"},
    "registry_product_kicker": {"title": "Реестр — подпись продукта", "body": "Программный комплекс"},
    "registry_product_name": {"title": "Реестр — название продукта", "body": "«Страж | Авангард»"},
    "registry_chip_1": {"title": "Реестр — чип 1", "body": "Импортозамещение"},
    "registry_chip_2": {"title": "Реестр — чип 2", "body": "Госсектор"},
    "registry_chip_3": {"title": "Реестр — чип 3", "body": "Объекты КИИ"},
    "registry_status_1_title": {"title": "Реестр — статус 1 заголовок", "body": "Статус"},
    "registry_status_1_value": {"title": "Реестр — статус 1 значение", "body": "В реестре ПО РФ"},
    "registry_status_1_desc": {"title": "Реестр — статус 1 описание", "body": "Подтверждена государственная регистрация"},
    "registry_status_2_title": {"title": "Реестр — статус 2 заголовок", "body": "Готовность"},
    "registry_status_2_value": {"title": "Реестр — статус 2 значение", "body": "Документы и выписки"},
    "registry_status_2_desc": {"title": "Реестр — статус 2 описание", "body": "Справки и реестровые сведения доступны"},
    "registry_status_3_title": {"title": "Реестр — статус 3 заголовок", "body": "Применение"},
    "registry_status_3_value": {"title": "Реестр — статус 3 значение", "body": "Госсектор и КИИ"},
    "registry_status_3_desc": {"title": "Реестр — статус 3 описание", "body": "Рекомендовано для критической инфраструктуры"},
    "registry_benefits_title": {"title": "Реестр — преимущества заголовок", "body": "Что это дает заказчику"},
    "registry_benefit_1": {"title": "Реестр — преимущество 1", "body": "Быстрое включение в конкурсную документацию"},
    "registry_benefit_2": {"title": "Реестр — преимущество 2", "body": "Уверенное импортозамещение и закупки 44/223‑ФЗ"},
    "registry_benefit_3": {"title": "Реестр — преимущество 3", "body": "Прозрачная подтверждаемая цепочка владения ПО"},
    "registry_benefit_4": {"title": "Реестр — преимущество 4", "body": "Поддержка требований регуляторов и ИБ"},
    "registry_steps_title": {"title": "Реестр — шаги заголовок", "body": "Как использовать регистрацию"},
    "registry_step_1": {"title": "Реестр — шаг 1", "body": "Скачайте выписку и приложите к проектной документации"},
    "registry_step_2": {"title": "Реестр — шаг 2", "body": "Укажите реестровый статус в закупочной спецификации"},
    "registry_step_3": {"title": "Реестр — шаг 3", "body": "При аудите предоставьте комплект подтверждающих файлов"},
    "registry_footer_brand": {"title": "Реестр — подпись внизу слева", "body": "Минцифры России"},
    "registry_footer_note": {"title": "Реестр — подпись внизу справа", "body": "Реестр отечественного ПО"},
    "registry_docs_title": {"title": "Реестр — заголовок документов", "body": "Документы"},
    "features_title": {"title": "Возможности — заголовок", "body": "Ключевые возможности"},
    "features_subtitle": {
        "title": "Возможности — подзаголовок",
        "body": "Инновационные решения для обеспечения безопасности объектов любой сложности.",
    },
    "feature_1_title": {"title": "Фича 1 — заголовок", "body": "Биометрический доступ"},
    "feature_1_desc": {"title": "Фича 1 — описание", "body": "Распознавание лиц и отпечатков пальцев за доли секунды."},
    "feature_2_title": {"title": "Фича 2 — заголовок", "body": "Учет рабочего времени"},
    "feature_2_desc": {"title": "Фича 2 — описание", "body": "Автоматическое формирование табелей и интеграция с 1С."},
    "feature_3_title": {"title": "Фича 3 — заголовок", "body": "Аппаратная независимость"},
    "feature_3_desc": {
        "title": "Фича 3 — описание",
        "body": "Поддержка контроллеров различных производителей и протоколов взаимодействия.",
    },
    "feature_4_title": {"title": "Фича 4 — заголовок", "body": "Anti-passback"},
    "feature_4_desc": {"title": "Фича 4 — описание", "body": "Глобальная защита от двойного прохода на всей территории предприятия."},
    "advantages_title": {
        "title": "Преимущества — заголовок",
        "body": "Преимущества СКУД «Авангардъ»",
    },
    "advantages_subtitle": {
        "title": "Преимущества — подзаголовок",
        "body": "Фокус на надежность, масштабирование и соответствие требованиям регуляторов и служб безопасности.",
    },
    "adv_1_title": {"title": "Преимущество 1 — заголовок", "body": "Безопасность и контроль"},
    "adv_1_desc": {
        "title": "Преимущество 1 — описание",
        "body": "Гибкое разграничение прав, журналирование событий, контроль доступа по зонам и сценариям.",
    },
    "adv_2_title": {"title": "Преимущество 2 — заголовок", "body": "Масштабируемая архитектура"},
    "adv_2_desc": {
        "title": "Преимущество 2 — описание",
        "body": "Единое управление для филиалов и распределенных объектов без потери производительности.",
    },
    "adv_3_title": {"title": "Преимущество 3 — заголовок", "body": "Регуляторная готовность"},
    "adv_3_desc": {
        "title": "Преимущество 3 — описание",
        "body": "Подтвержденный статус в реестре ПО РФ и комплект документов для закупок и проверок.",
    },
    "adv_4_title": {"title": "Преимущество 4 — заголовок", "body": "Гибкая интеграция"},
    "adv_4_desc": {
        "title": "Преимущество 4 — описание",
        "body": "Интеграции с видеонаблюдением, системами учета и внешними сервисами через API.",
    },
    "adv_5_title": {"title": "Преимущество 5 — заголовок", "body": "Надежность 24/7"},
    "adv_5_desc": {
        "title": "Преимущество 5 — описание",
        "body": "Отказоустойчивые компоненты и стабильная работа при высокой нагрузке.",
    },
    "adv_6_title": {"title": "Преимущество 6 — заголовок", "body": "Быстрое внедрение"},
    "adv_6_desc": {
        "title": "Преимущество 6 — описание",
        "body": "Готовые сценарии, шаблоны и методики запуска сокращают сроки внедрения.",
    },
    "safety_title": {"title": "Безопасность — заголовок", "body": "Безопасность и контроль доступа"},
    "safety_content": {
        "title": "Безопасность — текст",
        "body": "СКУД «Стражъ | Авангардъ» обеспечивает надёжную защиту периметра и контроль доступа на объекты любой сложности.",
    },
    "safety_key_features_title": {"title": "Безопасность — подзаголовок", "body": "Ключевые возможности"},
    "safety_key_features_body": {
        "title": "Безопасность — анонс",
        "body": "Контроль доступа, аудит событий и поддержка строгих сценариев безопасности.",
    },
    "safety_kf_1_icon": {"title": "Безопасность — ключевая возможность 1 (иконка)", "body": "user"},
    "safety_kf_1_title": {"title": "Безопасность — ключевая возможность 1 (заголовок)", "body": "Многоуровневая идентификация"},
    "safety_kf_1_desc": {
        "title": "Безопасность — ключевая возможность 1 (текст)",
        "body": "Поддержка карт, биометрии, PIN-кодов и мобильных приложений",
    },
    "safety_kf_2_icon": {"title": "Безопасность — ключевая возможность 2 (иконка)", "body": "clock"},
    "safety_kf_2_title": {"title": "Безопасность — ключевая возможность 2 (заголовок)", "body": "Контроль времени доступа"},
    "safety_kf_2_desc": {
        "title": "Безопасность — ключевая возможность 2 (текст)",
        "body": "Гибкие правила доступа по времени и дням недели",
    },
    "safety_kf_3_icon": {"title": "Безопасность — ключевая возможность 3 (иконка)", "body": "monitor"},
    "safety_kf_3_title": {"title": "Безопасность — ключевая возможность 3 (заголовок)", "body": "Журнал событий"},
    "safety_kf_3_desc": {
        "title": "Безопасность — ключевая возможность 3 (текст)",
        "body": "Полный аудит всех действий в системе с возможностью экспорта",
    },
    "safety_kf_4_icon": {"title": "Безопасность — ключевая возможность 4 (иконка)", "body": "shield"},
    "safety_kf_4_title": {"title": "Безопасность — ключевая возможность 4 (заголовок)", "body": "Антитеррористическая защита"},
    "safety_kf_4_desc": {
        "title": "Безопасность — ключевая возможность 4 (текст)",
        "body": "Соответствие требованиям безопасности для объектов КИИ",
    },
    "scalability_title": {"title": "Масштабируемость — заголовок", "body": "Масштабируемая архитектура"},
    "scalability_content": {
        "title": "Масштабируемость — текст",
        "body": "Система легко масштабируется от небольшого офиса до крупного предприятия с тысячами точек доступа.",
    },
    "scalability_key_features_title": {
        "title": "Масштабируемость — подзаголовок",
        "body": "Возможности масштабирования",
    },
    "scalability_key_features_body": {
        "title": "Масштабируемость — анонс",
        "body": "Поддержка роста от одного офиса до распределённой сети объектов.",
    },
    "scalability_kf_1_icon": {"title": "Масштабируемость — ключевая возможность 1 (иконка)", "body": "monitor"},
    "scalability_kf_1_title": {
        "title": "Масштабируемость — ключевая возможность 1 (заголовок)",
        "body": "Горизонтальное масштабирование",
    },
    "scalability_kf_1_desc": {
        "title": "Масштабируемость — ключевая возможность 1 (текст)",
        "body": "Добавление новых контроллеров без остановки системы",
    },
    "scalability_kf_2_icon": {"title": "Масштабируемость — ключевая возможность 2 (иконка)", "body": "shield"},
    "scalability_kf_2_title": {"title": "Масштабируемость — ключевая возможность 2 (заголовок)", "body": "Модульная архитектура"},
    "scalability_kf_2_desc": {
        "title": "Масштабируемость — ключевая возможность 2 (текст)",
        "body": "Возможность подключения дополнительных модулей по мере роста",
    },
    "scalability_kf_3_icon": {"title": "Масштабируемость — ключевая возможность 3 (иконка)", "body": "cloud"},
    "scalability_kf_3_title": {"title": "Масштабируемость — ключевая возможность 3 (заголовок)", "body": "Облачные технологии"},
    "scalability_kf_3_desc": {
        "title": "Масштабируемость — ключевая возможность 3 (текст)",
        "body": "Использование облачных сервисов для обработки больших данных",
    },
    "scalability_kf_4_icon": {"title": "Масштабируемость — ключевая возможность 4 (иконка)", "body": "network"},
    "scalability_kf_4_title": {
        "title": "Масштабируемость — ключевая возможность 4 (заголовок)",
        "body": "Распределённая обработка",
    },
    "scalability_kf_4_desc": {
        "title": "Масштабируемость — ключевая возможность 4 (текст)",
        "body": "Балансировка нагрузки между серверами",
    },
    "monitoring_title": {"title": "Мониторинг — заголовок", "body": "Регулярная готовность и мониторинг"},
    "monitoring_content": {
        "title": "Мониторинг — текст",
        "body": "Круглосуточный мониторинг состояния системы и своевременное реагирование на события.",
    },
    "monitoring_key_features_title": {"title": "Мониторинг — подзаголовок", "body": "Возможности мониторинга"},
    "monitoring_key_features_body": {
        "title": "Мониторинг — анонс",
        "body": "Состояние системы, уведомления и отчёты — в одном интерфейсе.",
    },
    "monitoring_kf_1_icon": {"title": "Мониторинг — ключевая возможность 1 (иконка)", "body": "clock"},
    "monitoring_kf_1_title": {"title": "Мониторинг — ключевая возможность 1 (заголовок)", "body": "Реальное время"},
    "monitoring_kf_1_desc": {
        "title": "Мониторинг — ключевая возможность 1 (текст)",
        "body": "Мониторинг состояния всех компонентов системы в реальном времени",
    },
    "monitoring_kf_2_icon": {"title": "Мониторинг — ключевая возможность 2 (иконка)", "body": "bell"},
    "monitoring_kf_2_title": {"title": "Мониторинг — ключевая возможность 2 (заголовок)", "body": "Уведомления"},
    "monitoring_kf_2_desc": {
        "title": "Мониторинг — ключевая возможность 2 (текст)",
        "body": "Мгновенные оповещения о критических событиях по SMS и email",
    },
    "monitoring_kf_3_icon": {"title": "Мониторинг — ключевая возможность 3 (иконка)", "body": "tools"},
    "monitoring_kf_3_title": {"title": "Мониторинг — ключевая возможность 3 (заголовок)", "body": "Диагностика"},
    "monitoring_kf_3_desc": {
        "title": "Мониторинг — ключевая возможность 3 (текст)",
        "body": "Автоматическая диагностика неисправностей и предиктивное обслуживание",
    },
    "monitoring_kf_4_icon": {"title": "Мониторинг — ключевая возможность 4 (иконка)", "body": "report"},
    "monitoring_kf_4_title": {"title": "Мониторинг — ключевая возможность 4 (заголовок)", "body": "Отчётность"},
    "monitoring_kf_4_desc": {
        "title": "Мониторинг — ключевая возможность 4 (текст)",
        "body": "Подробные отчёты о работе системы с графиками и аналитикой",
    },
    "integration_title": {"title": "Интеграция — заголовок", "body": "Гибкая интеграция"},
    "integration_content": {
        "title": "Интеграция — текст",
        "body": "Легкая интеграция с существующими системами безопасности и корпоративными приложениями.",
    },
    "integration_key_features_title": {"title": "Интеграция — подзаголовок", "body": "Возможности интеграции"},
    "integration_key_features_body": {
        "title": "Интеграция — анонс",
        "body": "API, базы данных и связки с внешними системами безопасности.",
    },
    "integration_kf_1_icon": {"title": "Интеграция — ключевая возможность 1 (иконка)", "body": "link"},
    "integration_kf_1_title": {"title": "Интеграция — ключевая возможность 1 (заголовок)", "body": "API и SDK"},
    "integration_kf_1_desc": {
        "title": "Интеграция — ключевая возможность 1 (текст)",
        "body": "Полный набор API для интеграции с любыми приложениями",
    },
    "integration_kf_2_icon": {"title": "Интеграция — ключевая возможность 2 (иконка)", "body": "database"},
    "integration_kf_2_title": {"title": "Интеграция — ключевая возможность 2 (заголовок)", "body": "Базы данных"},
    "integration_kf_2_desc": {
        "title": "Интеграция — ключевая возможность 2 (текст)",
        "body": "Поддержка популярных СУБД: PostgreSQL, MySQL, Oracle, MS SQL",
    },
    "integration_kf_3_icon": {"title": "Интеграция — ключевая возможность 3 (иконка)", "body": "camera"},
    "integration_kf_3_title": {"title": "Интеграция — ключевая возможность 3 (заголовок)", "body": "Видеонаблюдение"},
    "integration_kf_3_desc": {
        "title": "Интеграция — ключевая возможность 3 (текст)",
        "body": "Интеграция с системами видеонаблюдения и распознавания лиц",
    },
    "integration_kf_4_icon": {"title": "Интеграция — ключевая возможность 4 (иконка)", "body": "shield"},
    "integration_kf_4_title": {
        "title": "Интеграция — ключевая возможность 4 (заголовок)",
        "body": "СКУД сторонних производителей",
    },
    "integration_kf_4_desc": {
        "title": "Интеграция — ключевая возможность 4 (текст)",
        "body": "Совместимость с оборудованием различных производителей",
    },
    "reliability_title": {"title": "Надёжность — заголовок", "body": "Надёжность 24/7"},
    "reliability_content": {
        "title": "Надёжность — текст",
        "body": "Бесперебойная работа системы круглосуточно с гарантированной доступностью.",
    },
    "reliability_key_features_title": {"title": "Надёжность — подзаголовок", "body": "Компоненты надёжности"},
    "reliability_key_features_body": {
        "title": "Надёжность — анонс",
        "body": "Отказоустойчивость, автономная работа и самодиагностика.",
    },
    "reliability_kf_1_icon": {"title": "Надёжность — ключевая возможность 1 (иконка)", "body": "shield"},
    "reliability_kf_1_title": {"title": "Надёжность — ключевая возможность 1 (заголовок)", "body": "Резервирование"},
    "reliability_kf_1_desc": {
        "title": "Надёжность — ключевая возможность 1 (текст)",
        "body": "Горячее резервирование критических компонентов системы",
    },
    "reliability_kf_2_icon": {"title": "Надёжность — ключевая возможность 2 (иконка)", "body": "clock"},
    "reliability_kf_2_title": {"title": "Надёжность — ключевая возможность 2 (заголовок)", "body": "Автономность"},
    "reliability_kf_2_desc": {
        "title": "Надёжность — ключевая возможность 2 (текст)",
        "body": "Работа в автономном режиме при отсутствии связи с сервером",
    },
    "reliability_kf_3_icon": {"title": "Надёжность — ключевая возможность 3 (иконка)", "body": "tools"},
    "reliability_kf_3_title": {"title": "Надёжность — ключевая возможность 3 (заголовок)", "body": "Самодиагностика"},
    "reliability_kf_3_desc": {
        "title": "Надёжность — ключевая возможность 3 (текст)",
        "body": "Автоматическое выявление и устранение неисправностей",
    },
    "reliability_kf_4_icon": {"title": "Надёжность — ключевая возможность 4 (иконка)", "body": "sla"},
    "reliability_kf_4_title": {"title": "Надёжность — ключевая возможность 4 (заголовок)", "body": "Безотказность"},
    "reliability_kf_4_desc": {
        "title": "Надёжность — ключевая возможность 4 (текст)",
        "body": "Гарантированная доступность 99.9% с SLA",
    },
    "deployment_title": {"title": "Внедрение — заголовок", "body": "Быстрое внедрение"},
    "deployment_content": {
        "title": "Внедрение — текст",
        "body": "Минимальные сроки внедрения системы с полным сопровождением на каждом этапе.",
    },
    "deployment_key_features_title": {"title": "Внедрение — подзаголовок", "body": "Этапы внедрения"},
    "deployment_key_features_body": {
        "title": "Внедрение — анонс",
        "body": "Понятный план внедрения от обследования до обучения сотрудников.",
    },
    "deployment_kf_1_icon": {"title": "Внедрение — ключевая возможность 1 (иконка)", "body": "checklist"},
    "deployment_kf_1_title": {"title": "Внедрение — ключевая возможность 1 (заголовок)", "body": "Обследование"},
    "deployment_kf_1_desc": {
        "title": "Внедрение — ключевая возможность 1 (текст)",
        "body": "Аудит объекта и разработка оптимального решения за 5 дней",
    },
    "deployment_kf_2_icon": {"title": "Внедрение — ключевая возможность 2 (иконка)", "body": "plan"},
    "deployment_kf_2_title": {"title": "Внедрение — ключевая возможность 2 (заголовок)", "body": "Проектирование"},
    "deployment_kf_2_desc": {
        "title": "Внедрение — ключевая возможность 2 (текст)",
        "body": "Разработка проектной документации и согласование решений",
    },
    "deployment_kf_3_icon": {"title": "Внедрение — ключевая возможность 3 (иконка)", "body": "tools"},
    "deployment_kf_3_title": {"title": "Внедрение — ключевая возможность 3 (заголовок)", "body": "Монтаж и пуск"},
    "deployment_kf_3_desc": {
        "title": "Внедрение — ключевая возможность 3 (текст)",
        "body": "Профессиональный монтаж оборудования и запуск системы",
    },
    "deployment_kf_4_icon": {"title": "Внедрение — ключевая возможность 4 (иконка)", "body": "user"},
    "deployment_kf_4_title": {"title": "Внедрение — ключевая возможность 4 (заголовок)", "body": "Обучение"},
    "deployment_kf_4_desc": {
        "title": "Внедрение — ключевая возможность 4 (текст)",
        "body": "Полное обучение персонала работе с системой",
    },
    "documents_title": {"title": "Документы — заголовок", "body": "Документация и прайс-листы"},
    "documents_subtitle": {
        "title": "Документы — подзаголовок",
        "body": "Вся необходимая информация для проектирования и закупок. Загружается через админку.",
    },
    "support_title": {"title": "Поддержка — заголовок", "body": "Техническая поддержка"},
    "support_subtitle": {
        "title": "Поддержка — подзаголовок",
        "body": "Наши специалисты отвечают по вопросам внедрения, настройки и эксплуатации системы «Стражъ | Авангардъ».",
    },
    "consent_title": {"title": "Согласие — заголовок", "body": "Cookies и персональные данные"},
    "consent_body": {
        "title": "Согласие — текст",
        "body": "Сайт использует файлы cookie, чтобы работать корректно. Нажимая кнопку «Согласен», вы подтверждаете согласие на обработку ваших персональных данных в рамках обращения в техподдержку.",
    },
    "contacts_phone": {"title": "Контакты — телефон", "body": "+7 (495) 123-45-67"},
    "contacts_email": {"title": "Контакты — e-mail", "body": "support@strazh-avangard.ru"},
    "contacts_address": {"title": "Контакты — адрес", "body": "г. Москва, Инновационный проезд, д. 1"},
    "requisites_company": {"title": "Реквизиты — организация", "body": ""},
    "requisites_inn": {"title": "Реквизиты — ИНН", "body": ""},
    "requisites_kpp": {"title": "Реквизиты — КПП", "body": ""},
    "requisites_ogrn": {"title": "Реквизиты — ОГРН", "body": ""},
    "requisites_address": {"title": "Реквизиты — адрес", "body": ""},
    "requisites_bank": {"title": "Реквизиты — банк", "body": ""},
    "requisites_bik": {"title": "Реквизиты — БИК", "body": ""},
    "requisites_rs": {"title": "Реквизиты — расчётный счёт", "body": ""},
    "requisites_ks": {"title": "Реквизиты — корреспондентский счёт", "body": ""},
    "option_turnstile_enabled": {"title": "Опции — Turnstile включён (0/1)", "body": "1"},
    "option_submit_min_interval_seconds": {"title": "Опции — антидубль форм (сек)", "body": "8"},
}

REGISTRY_EDITOR_SECTIONS: tuple[dict[str, object], ...] = (
    {
        "title": "Основное",
        "fields": (
            {"key": "registry_badge_label", "label": "Верхняя плашка", "type": "text"},
            {"key": "registry_title", "label": "Главный заголовок", "type": "textarea", "rows": 2},
            {"key": "registry_product_kicker", "label": "Подпись над названием", "type": "text"},
            {"key": "registry_product_name", "label": "Название продукта", "type": "text"},
            {"key": "registry_description", "label": "Основное описание", "type": "textarea", "rows": 4},
        ),
    },
    {
        "title": "Чипы",
        "fields": (
            {"key": "registry_chip_1", "label": "Чип 1", "type": "text"},
            {"key": "registry_chip_2", "label": "Чип 2", "type": "text"},
            {"key": "registry_chip_3", "label": "Чип 3", "type": "text"},
        ),
    },
    {
        "title": "Статусы",
        "fields": (
            {"key": "registry_status_1_title", "label": "Статус 1 — заголовок", "type": "text"},
            {"key": "registry_status_1_value", "label": "Статус 1 — значение", "type": "text"},
            {"key": "registry_status_1_desc", "label": "Статус 1 — описание", "type": "textarea", "rows": 2},
            {"key": "registry_status_2_title", "label": "Статус 2 — заголовок", "type": "text"},
            {"key": "registry_status_2_value", "label": "Статус 2 — значение", "type": "text"},
            {"key": "registry_status_2_desc", "label": "Статус 2 — описание", "type": "textarea", "rows": 2},
            {"key": "registry_status_3_title", "label": "Статус 3 — заголовок", "type": "text"},
            {"key": "registry_status_3_value", "label": "Статус 3 — значение", "type": "text"},
            {"key": "registry_status_3_desc", "label": "Статус 3 — описание", "type": "textarea", "rows": 2},
        ),
    },
    {
        "title": "Преимущества и шаги",
        "fields": (
            {"key": "registry_benefits_title", "label": "Заголовок преимуществ", "type": "text"},
            {"key": "registry_benefit_1", "label": "Преимущество 1", "type": "text"},
            {"key": "registry_benefit_2", "label": "Преимущество 2", "type": "text"},
            {"key": "registry_benefit_3", "label": "Преимущество 3", "type": "text"},
            {"key": "registry_benefit_4", "label": "Преимущество 4", "type": "text"},
            {"key": "registry_steps_title", "label": "Заголовок шагов", "type": "text"},
            {"key": "registry_step_1", "label": "Шаг 1", "type": "text"},
            {"key": "registry_step_2", "label": "Шаг 2", "type": "text"},
            {"key": "registry_step_3", "label": "Шаг 3", "type": "text"},
            {"key": "registry_docs_title", "label": "Заголовок документов", "type": "text"},
            {"key": "registry_footer_brand", "label": "Подпись внизу слева", "type": "text"},
            {"key": "registry_footer_note", "label": "Подпись внизу справа", "type": "text"},
        ),
    },
)


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    max_upload_mb_raw = (os.environ.get("MAX_UPLOAD_MB") or "").strip()
    if max_upload_mb_raw.isdigit():
        max_upload_mb = int(max_upload_mb_raw)
        if max_upload_mb == 0:
            app.config["MAX_CONTENT_LENGTH"] = None
        else:
            app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
    else:
        app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024 * 1024

    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    support_fts_available = True
    with engine.begin() as conn:
        columns = {r._mapping["name"] for r in conn.execute(text("PRAGMA table_info(support_messages)"))}
        if "company" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN company VARCHAR(200) NOT NULL DEFAULT ''"
                )
            )
        if "telegram" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN telegram TEXT NOT NULL DEFAULT ''"
                )
            )
        if "whatsapp" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN whatsapp TEXT NOT NULL DEFAULT ''"
                )
            )
        if "complaints" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN complaints TEXT NOT NULL DEFAULT ''"
                )
            )
        if "anydesk_id" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN anydesk_id VARCHAR(64) NOT NULL DEFAULT ''"
                )
            )
        if "staff_notes" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN staff_notes TEXT NOT NULL DEFAULT ''"
                )
            )
        if "user_id" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN user_id INTEGER NULL"
                )
            )

        admin_cols = {r._mapping["name"] for r in conn.execute(text("PRAGMA table_info(admin_users)"))}
        if "first_name" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN first_name VARCHAR(120) NOT NULL DEFAULT ''"))
        if "last_name" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN last_name VARCHAR(120) NOT NULL DEFAULT ''"))
        if "phone" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN phone TEXT NOT NULL DEFAULT ''"))
        if "email" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN email TEXT NOT NULL DEFAULT ''"))
        if "telegram" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN telegram TEXT NOT NULL DEFAULT ''"))
        if "whatsapp" not in admin_cols:
            conn.execute(text("ALTER TABLE admin_users ADD COLUMN whatsapp TEXT NOT NULL DEFAULT ''"))

        attachment_cols = {
            r._mapping["name"] for r in conn.execute(text("PRAGMA table_info(support_attachments)"))
        }
        if attachment_cols:
            if "direction" not in attachment_cols:
                conn.execute(
                    text(
                        "ALTER TABLE support_attachments "
                        "ADD COLUMN direction VARCHAR(16) NOT NULL DEFAULT 'from_client'"
                    )
                )
            if "note" not in attachment_cols:
                conn.execute(
                    text(
                        "ALTER TABLE support_attachments "
                        "ADD COLUMN note TEXT NOT NULL DEFAULT ''"
                    )
                )
            if "size_bytes" not in attachment_cols:
                conn.execute(
                    text(
                        "ALTER TABLE support_attachments "
                        "ADD COLUMN size_bytes INTEGER NOT NULL DEFAULT 0"
                    )
                )
        try:
            expected_fts_cols = {
                "name",
                "email",
                "company",
                "phone",
                "telegram",
                "whatsapp",
                "anydesk_id",
                "subject",
                "message",
                "complaints",
                "staff_notes",
            }
            existing_fts_cols = {
                r._mapping["name"]
                for r in conn.execute(text("PRAGMA table_info(support_messages_fts)"))
            }
            if existing_fts_cols and not expected_fts_cols.issubset(existing_fts_cols):
                conn.execute(text("DROP TRIGGER IF EXISTS support_messages_fts_ai"))
                conn.execute(text("DROP TRIGGER IF EXISTS support_messages_fts_ad"))
                conn.execute(text("DROP TRIGGER IF EXISTS support_messages_fts_au"))
                conn.execute(text("DROP TABLE IF EXISTS support_messages_fts"))
            conn.execute(
                text(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS support_messages_fts USING fts5("
                    "name, email, company, phone, telegram, whatsapp, anydesk_id, subject, message, complaints, staff_notes, "
                    "tokenize='unicode61'"
                    ")"
                )
            )
            conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS support_messages_fts_ai "
                    "AFTER INSERT ON support_messages BEGIN "
                    "INSERT INTO support_messages_fts(rowid, name, email, company, phone, telegram, whatsapp, anydesk_id, subject, message, complaints, staff_notes) "
                    "VALUES (new.id, new.name, new.email, new.company, new.phone, new.telegram, new.whatsapp, new.anydesk_id, new.subject, new.message, new.complaints, new.staff_notes); "
                    "END;"
                )
            )
            conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS support_messages_fts_ad "
                    "AFTER DELETE ON support_messages BEGIN "
                    "DELETE FROM support_messages_fts WHERE rowid = old.id; "
                    "END;"
                )
            )
            conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS support_messages_fts_au "
                    "AFTER UPDATE ON support_messages BEGIN "
                    "UPDATE support_messages_fts SET "
                    "name = new.name, "
                    "email = new.email, "
                    "company = new.company, "
                    "phone = new.phone, "
                    "telegram = new.telegram, "
                    "whatsapp = new.whatsapp, "
                    "anydesk_id = new.anydesk_id, "
                    "subject = new.subject, "
                    "message = new.message, "
                    "complaints = new.complaints, "
                    "staff_notes = new.staff_notes "
                    "WHERE rowid = new.id; "
                    "END;"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO support_messages_fts(rowid, name, email, company, phone, telegram, whatsapp, anydesk_id, subject, message, complaints, staff_notes) "
                    "SELECT id, name, email, company, phone, telegram, whatsapp, anydesk_id, subject, message, complaints, staff_notes "
                    "FROM support_messages "
                    "WHERE id NOT IN (SELECT rowid FROM support_messages_fts)"
                )
            )
        except Exception:
            support_fts_available = False

    app.config["SUPPORT_FTS_AVAILABLE"] = support_fts_available

    @app.before_request
    def _open_db() -> None:
        g.db = SessionLocal()

    @app.errorhandler(413)
    def _file_too_large(_err):
        flash("Слишком большой файл. Уменьшите размер или загрузите по частям.", "danger")
        return redirect(request.referrer or url_for("admin_messages"))

    @app.teardown_request
    def _close_db(exc: BaseException | None) -> None:
        db: Session | None = g.pop("db", None)
        if db is None:
            return
        try:
            if exc is None:
                db.commit()
            else:
                db.rollback()
        finally:
            db.close()

    def db() -> Session:
        return g.db

    def ensure_defaults() -> None:
        def _norm(s: str) -> str:
            return "".join([ch.lower() if ch.isalnum() else " " for ch in (s or "")]).split()

        existing = set(db().scalars(select(ContentBlock.key)).all())
        created = False
        slogan_body: str | None = None
        if "slogan" not in existing:
            old_primary = db().get(ContentBlock, "brand_primary")
            old_secondary = db().get(ContentBlock, "brand_secondary")
            merged = " ".join(
                [p for p in [getattr(old_primary, "body", ""), getattr(old_secondary, "body", "")] if p]
            ).strip()
            brand_full = db().get(ContentBlock, "brand_full")
            brand_full_body = getattr(brand_full, "body", "")
            merged_tokens = set(_norm(merged))
            brand_tokens = set(_norm(brand_full_body))
            if merged and merged_tokens and not merged_tokens.issubset(brand_tokens):
                slogan_body = merged
        else:
            old_primary = db().get(ContentBlock, "brand_primary")
            old_secondary = db().get(ContentBlock, "brand_secondary")
            merged = " ".join(
                [p for p in [getattr(old_primary, "body", ""), getattr(old_secondary, "body", "")] if p]
            ).strip()
            slogan = db().get(ContentBlock, "slogan")
            if slogan is not None and merged and _norm(slogan.body) == _norm(merged):
                slogan.title = DEFAULT_CONTENT["slogan"]["title"]
                slogan.body = DEFAULT_CONTENT["slogan"]["body"]
                created = True

        for key, payload in DEFAULT_CONTENT.items():
            if key in existing:
                continue
            body = payload["body"]
            if key == "slogan" and slogan_body is not None:
                body = slogan_body
            db().add(ContentBlock(key=key, title=payload["title"], body=body))
            created = True

        def extract_text(value: str) -> str:
            return re.sub(r"<[^>]+>", " ", (value or "")).replace("\xa0", " ").strip()

        def migrate_key_features(prefix: str, title_key: str, body_key: str) -> None:
            nonlocal created
            body_block = db().get(ContentBlock, body_key)
            if body_block is None:
                return
            body = body_block.body or ""
            if "<div class=\"col-md-6\">" not in body and "<div class='col-md-6'>" not in body:
                return
            titles = [extract_text(m) for m in re.findall(r"<h5[^>]*>(.*?)</h5>", body, flags=re.IGNORECASE | re.DOTALL)]
            descs = [extract_text(m) for m in re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.IGNORECASE | re.DOTALL)]
            for idx in range(1, 5):
                t = titles[idx - 1] if len(titles) >= idx else ""
                d = descs[idx - 1] if len(descs) >= idx else ""
                title_block = db().get(ContentBlock, f"{prefix}_kf_{idx}_title")
                desc_block = db().get(ContentBlock, f"{prefix}_kf_{idx}_desc")
                if title_block is not None and t:
                    title_block.body = t
                    created = True
                if desc_block is not None and d:
                    desc_block.body = d
                    created = True
            body_block.body = ""
            created = True

        hero_label = db().get(ContentBlock, "hero_mockup_label")
        if hero_label is not None:
            placeholder_variants = [["strazh", "admin", "panel"], ["straz", "admin", "panel"]]
            current_norm = _norm(hero_label.body)
            if any(current_norm == variant for variant in placeholder_variants):
                hero_label.title = DEFAULT_CONTENT["hero_mockup_label"]["title"]
                hero_label.body = DEFAULT_CONTENT["hero_mockup_label"]["body"]
                created = True

        hero_cta_secondary = db().get(ContentBlock, "hero_cta_secondary")
        if hero_cta_secondary is not None and _norm(hero_cta_secondary.body) == _norm("Скачать прайс"):
            hero_cta_secondary.title = DEFAULT_CONTENT["hero_cta_secondary"]["title"]
            hero_cta_secondary.body = DEFAULT_CONTENT["hero_cta_secondary"]["body"]
            created = True

        migrate_key_features("safety", "safety_key_features_title", "safety_key_features_body")
        migrate_key_features("scalability", "scalability_key_features_title", "scalability_key_features_body")
        migrate_key_features("monitoring", "monitoring_key_features_title", "monitoring_key_features_body")
        migrate_key_features("integration", "integration_key_features_title", "integration_key_features_body")
        migrate_key_features("reliability", "reliability_key_features_title", "reliability_key_features_body")
        migrate_key_features("deployment", "deployment_key_features_title", "deployment_key_features_body")

        if created:
            db().flush()

        default_doc_categories = [
            ("price", "Прайс", 10),
            ("registry", "Реестр ПО РФ", 20),
            ("other", "Документы", 30),
        ]
        existing_doc_categories = set(db().scalars(select(DocumentCategory.key)).all())
        if not existing_doc_categories:
            for key, title, order in default_doc_categories:
                db().add(DocumentCategory(key=key, title=title, sort_order=order))
            db().flush()
        else:
            for key, title, order in default_doc_categories:
                if key in existing_doc_categories:
                    continue
                db().add(DocumentCategory(key=key, title=title, sort_order=order))
            db().flush()

    def current_user() -> AdminUser | None:
        user_id = session.get("admin_user_id")
        if not user_id:
            return None
        return db().get(AdminUser, int(user_id))

    def login_required(view: Callable[..., object]) -> Callable[..., object]:
        def wrapped(*args: object, **kwargs: object) -> object:
            if current_user() is None:
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)

        wrapped.__name__ = view.__name__
        return wrapped

    def current_client() -> User | None:
        user_id = session.get("user_id")
        if not user_id:
            return None
        return db().get(User, int(user_id))

    def client_login_required(view: Callable[..., object]) -> Callable[..., object]:
        def wrapped(*args: object, **kwargs: object) -> object:
            if current_client() is None:
                return redirect(url_for("login", next=request.path))
            return view(*args, **kwargs)

        wrapped.__name__ = view.__name__
        return wrapped

    def get_blocks() -> dict[str, ContentBlock]:
        ensure_defaults()
        blocks = db().scalars(select(ContentBlock)).all()
        return {b.key: b for b in blocks}

    def get_asset_by_slot(slot_key: str) -> Asset | None:
        return db().scalar(select(Asset).where(Asset.slot_key == slot_key))

    @app.context_processor
    def inject_site_assets():
        return {
            "logo_asset": get_asset_by_slot("site_logo"),
            "favicon_asset": get_asset_by_slot("site_favicon"),
            "client_user": current_client(),
        }

    def allowed_file(filename: str, exts: set[str]) -> bool:
        if "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in exts

    def safe_next_url(next_url: str | None) -> str | None:
        if not next_url:
            return None
        parsed = urlparse(next_url)
        if parsed.scheme or parsed.netloc:
            return None
        if not next_url.startswith("/"):
            return None
        return next_url

    def remote_ip() -> str:
        return (
            (request.headers.get("CF-Connecting-IP") or "").strip()
            or (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            or (request.remote_addr or "").strip()
        )

    def log_user_event(event: str, user_id: int | None, details: object | None = None) -> None:
        payload = ""
        if details is None:
            payload = ""
        elif isinstance(details, str):
            payload = details
        else:
            try:
                payload = json.dumps(details, ensure_ascii=False)
            except TypeError:
                payload = str(details)
        db().add(
            UserEventLog(
                user_id=user_id,
                event=(event or "").strip(),
                ip=remote_ip(),
                user_agent=(request.headers.get("User-Agent") or ""),
                details=payload,
                created_at=datetime.utcnow(),
            )
        )

    def _messages_like(value: str) -> str:
        return f"%{(value or '').replace('%', '\\%').replace('_', '\\_')}%"

    def _messages_ci_like(col, value: str):
        return func.lower(col).like(_messages_like(value).lower(), escape="\\")

    def _parse_date(value: str) -> datetime | None:
        try:
            return datetime.strptime((value or "").strip(), "%Y-%m-%d")
        except ValueError:
            return None

    def _fts_term(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", (value or "")).strip()
        if not cleaned:
            return ""
        if cleaned.endswith("*"):
            return cleaned
        return f"{cleaned}*"

    def _fts_safe_token(value: str) -> bool:
        v = (value or "").strip()
        if len(v) < 2:
            return False
        return all(ch.isalnum() for ch in v)

    def build_messages_query(q: str) -> tuple[list[object], str | None]:
        tokens = [t for t in (q or "").strip().split() if t]
        if not tokens:
            return ([], None)

        conditions: list[object] = []
        fts_parts: list[str] = []
        for token in tokens:
            field = ""
            value = token
            if ":" in token:
                field, value = token.split(":", 1)
                field = field.strip().lower()
                value = value.strip()
            value = value.strip()
            if not value:
                continue

            if field in {"id", "#"}:
                try:
                    msg_id = int(value)
                except ValueError:
                    continue
                conditions.append(SupportMessage.id == msg_id)
                continue

            if field == "status":
                conditions.append(SupportMessage.status == value)
                continue

            if field in {"from", "date_from"}:
                dt = _parse_date(value)
                if dt is not None:
                    conditions.append(SupportMessage.created_at >= dt)
                continue

            if field in {"to", "date_to"}:
                dt = _parse_date(value)
                if dt is not None:
                    dt0 = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                    conditions.append(SupportMessage.created_at < dt0 + timedelta(days=1))
                continue

            if field in {"name", "email", "company", "phone", "telegram", "whatsapp", "anydesk_id"}:
                col = getattr(SupportMessage, field)
                conditions.append(_messages_ci_like(col, value))
                continue

            if field in {"subject", "message", "complaints", "staff_notes"}:
                col = getattr(SupportMessage, field)
                conditions.append(_messages_ci_like(col, value))
                if app.config.get("SUPPORT_FTS_AVAILABLE") and _fts_safe_token(value):
                    fts_parts.append(f"{field}:{_fts_term(value)}")
                else:
                    pass
                continue

            if app.config.get("SUPPORT_FTS_AVAILABLE"):
                if _fts_safe_token(value):
                    fts_parts.append(_fts_term(value))
            conditions.append(
                or_(
                    _messages_ci_like(SupportMessage.name, value),
                    _messages_ci_like(SupportMessage.email, value),
                    _messages_ci_like(SupportMessage.company, value),
                    _messages_ci_like(SupportMessage.phone, value),
                    _messages_ci_like(SupportMessage.telegram, value),
                    _messages_ci_like(SupportMessage.whatsapp, value),
                    _messages_ci_like(SupportMessage.anydesk_id, value),
                    _messages_ci_like(SupportMessage.subject, value),
                    _messages_ci_like(SupportMessage.message, value),
                    _messages_ci_like(SupportMessage.complaints, value),
                    _messages_ci_like(SupportMessage.staff_notes, value),
                )
            )

        fts_query = " AND ".join([p for p in fts_parts if p]) if fts_parts else None
        return (conditions, fts_query)

    def _turnstile_site_key() -> str:
        return (
            (os.environ.get("CF_TURNSTILE_SITE_KEY") or "")
            or (os.environ.get("TURNSTILE_SITE_KEY") or "")
        ).strip()

    def _turnstile_secret_key() -> str:
        return (
            (os.environ.get("CF_TURNSTILE_SECRET_KEY") or "")
            or (os.environ.get("TURNSTILE_SECRET_KEY") or "")
        ).strip()

    def turnstile_enabled() -> bool:
        if not _turnstile_site_key() or not _turnstile_secret_key():
            return False
        block = db().get(ContentBlock, "option_turnstile_enabled")
        raw = (getattr(block, "body", "") or "").strip().lower()
        if not raw:
            return True
        return raw in {"1", "true", "yes", "y", "on"}

    def verify_turnstile(token: str, remote_ip: str | None) -> bool:
        secret_key = _turnstile_secret_key()
        if not secret_key:
            return True
        token = (token or "").strip()
        if not token:
            return False
        payload = {"secret": secret_key, "response": token}
        if remote_ip:
            payload["remoteip"] = remote_ip
        body = urlencode(payload).encode("utf-8")
        req = Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=4) as resp:
                data = resp.read().decode("utf-8", errors="replace")
        except URLError:
            return False
        try:
            result = json.loads(data)
        except json.JSONDecodeError:
            return False
        return bool(result.get("success"))

    def looks_like_bot_headers() -> bool:
        ua = (request.headers.get("User-Agent") or "").strip()
        if not ua or len(ua) < 10:
            return True
        ua_l = ua.lower()
        blocked_fragments = (
            "python-requests",
            "curl/",
            "wget/",
            "aiohttp",
            "httpclient",
            "libwww-perl",
            "scrapy",
            "go-http-client",
        )
        if any(f in ua_l for f in blocked_fragments):
            return True
        if "bot" in ua_l or "spider" in ua_l or "crawler" in ua_l:
            return True

        ct = (request.headers.get("Content-Type") or "").lower()
        if not (ct.startswith("application/x-www-form-urlencoded") or ct.startswith("multipart/form-data")):
            return True

        origin = (request.headers.get("Origin") or "").strip()
        referer = (request.headers.get("Referer") or "").strip()
        host_url = request.host_url.rstrip("/")
        if origin:
            if not origin.startswith(host_url):
                return True
        elif referer:
            if not referer.startswith(host_url):
                return True
        else:
            if not (request.headers.get("Accept-Language") or "").strip():
                return True

        return False

    def submit_min_interval_seconds() -> int:
        env_raw = (
            (os.environ.get("GUARDE_SUBMIT_MIN_INTERVAL_SECONDS") or "")
            or (os.environ.get("SUBMIT_MIN_INTERVAL_SECONDS") or "")
        ).strip()
        raw = env_raw
        if not raw:
            block = db().get(ContentBlock, "option_submit_min_interval_seconds")
            raw = (getattr(block, "body", "") or "").strip()
        try:
            value = int(raw)
        except ValueError:
            value = 8
        if value < 0:
            value = 0
        if value > 300:
            value = 300
        return value

    def issue_submit_token(form_key: str) -> str:
        state = session.get("_submit_state")
        if not isinstance(state, dict):
            state = {}
        form_state = state.get(form_key)
        if not isinstance(form_state, dict):
            form_state = {}
        token = secrets.token_urlsafe(18)
        form_state["token"] = token
        form_state["issued_at"] = int(time.time())
        state[form_key] = form_state
        session["_submit_state"] = state
        session.modified = True
        return token

    def consume_submit_token(form_key: str, token: str) -> tuple[bool, str]:
        state = session.get("_submit_state")
        if not isinstance(state, dict):
            return (False, "missing")
        form_state = state.get(form_key)
        if not isinstance(form_state, dict):
            return (False, "missing")
        expected = (form_state.get("token") or "").strip()
        token = (token or "").strip()
        if not expected or not token or token != expected:
            return (False, "invalid")
        now = int(time.time())
        last_submit_at = int(form_state.get("last_submit_at") or 0)
        min_interval = submit_min_interval_seconds()
        if min_interval and last_submit_at and now - last_submit_at < min_interval:
            return (False, "too_fast")
        form_state["last_submit_at"] = now
        form_state.pop("token", None)
        state[form_key] = form_state
        session["_submit_state"] = state
        session.modified = True
        return (True, "ok")

    def store_upload(file_storage, kind: str) -> tuple[str, str]:
        original_name = file_storage.filename or ""
        safe = secure_filename(original_name)
        if not safe or "." not in safe:
            raise ValueError("Имя файла не содержит расширения.")
        ext = safe.rsplit(".", 1)[1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        file_storage.save(UPLOAD_DIR / stored)
        return stored, original_name

    def normalize_multivalue(raw: str) -> str:
        v = (raw or "").replace("\r", "\n")
        v = v.replace(",", "\n").replace(";", "\n")
        parts = [p.strip() for p in v.split("\n")]
        parts = [p for p in parts if p]
        return "\n".join(parts)

    def store_support_upload_in_dir(file_storage, rel_dir: Path) -> tuple[str, str, int]:
        original_name = file_storage.filename or ""
        safe = secure_filename(original_name)
        ext = safe.rsplit(".", 1)[1].lower() if safe and "." in safe else ""
        store_as_zip = (not ext) or (ext not in ALLOWED_SUPPORT_UPLOAD_EXTS)
        stored_ext = "zip" if store_as_zip else ext
        rel = rel_dir / f"{uuid.uuid4().hex}.{stored_ext}"
        abs_path = UPLOAD_DIR / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if store_as_zip:
            arcname = secure_filename(original_name) or "file"
            with zipfile.ZipFile(abs_path, mode="w", compression=zipfile.ZIP_STORED) as zf:
                with zf.open(arcname, "w") as dst:
                    while True:
                        chunk = file_storage.stream.read(8 * 1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
        else:
            file_storage.save(abs_path)
        try:
            size_bytes = int(abs_path.stat().st_size)
        except OSError:
            size_bytes = 0
        return str(rel).replace("\\", "/"), original_name, size_bytes

    def store_support_upload(file_storage, msg_id: int) -> tuple[str, str, int]:
        return store_support_upload_in_dir(file_storage, Path("support") / str(msg_id))

    def delete_support_complaint_media(message_ids: list[int]) -> None:
        if not message_ids:
            return
        rows = db().scalars(
            select(SupportComplaintMedia).where(SupportComplaintMedia.message_id.in_(message_ids))
        ).all()
        for r in rows:
            try:
                (UPLOAD_DIR / r.stored_filename).unlink(missing_ok=True)
            except OSError:
                pass
            db().delete(r)

    def delete_support_worklog_media(log_ids: list[int]) -> None:
        if not log_ids:
            return
        rows = db().scalars(
            select(SupportWorkLogMedia).where(SupportWorkLogMedia.work_log_id.in_(log_ids))
        ).all()
        for r in rows:
            try:
                (UPLOAD_DIR / r.stored_filename).unlink(missing_ok=True)
            except OSError:
                pass
            db().delete(r)

    def delete_support_attachments(message_ids: list[int]) -> None:
        if not message_ids:
            return
        atts = db().scalars(select(SupportAttachment).where(SupportAttachment.message_id.in_(message_ids))).all()
        for att in atts:
            try:
                (UPLOAD_DIR / att.stored_filename).unlink(missing_ok=True)
            except OSError:
                pass
            db().delete(att)

    def delete_support_work_logs(message_ids: list[int]) -> None:
        if not message_ids:
            return
        log_ids = db().scalars(
            select(SupportWorkLog.id).where(SupportWorkLog.message_id.in_(message_ids))
        ).all()
        delete_support_worklog_media([int(x) for x in log_ids])
        db().execute(delete(SupportWorkLog).where(SupportWorkLog.message_id.in_(message_ids)))

    @app.get("/uploads/<path:filename>")
    def uploads(filename: str):
        asset = db().scalar(select(Asset).where(Asset.stored_filename == filename))
        if asset is not None and asset.kind == "doc" and (asset.category or "") == "download":
            if current_client() is None and current_user() is None:
                abort(404)
        return send_from_directory(UPLOAD_DIR, filename)

    @app.get("/favicon.ico")
    def favicon():
        asset = get_asset_by_slot("site_favicon")
        if asset is None:
            abort(404)
        return send_from_directory(UPLOAD_DIR, asset.stored_filename)

    @app.before_request
    def _support_bot_guard() -> None:
        if request.method == "POST" and request.path == "/support":
            if looks_like_bot_headers():
                abort(400)

    @app.before_request
    def _login_bot_guard() -> None:
        if request.method == "POST" and request.path == "/login":
            if looks_like_bot_headers():
                abort(400)

    @app.before_request
    def _forgot_password_bot_guard() -> None:
        if request.method == "POST" and request.path == "/forgot-password":
            if looks_like_bot_headers():
                abort(400)

    @app.before_request
    def _register_bot_guard() -> None:
        if request.method == "POST" and request.path == "/register":
            if looks_like_bot_headers():
                abort(400)

    @app.get("/")
    def index():
        blocks = get_blocks()
        ensure_defaults()
        doc_categories = (
            db()
            .scalars(select(DocumentCategory).order_by(DocumentCategory.sort_order.asc(), DocumentCategory.title.asc()))
            .all()
        )
        docs = (
            db()
            .scalars(
                select(Asset)
                .where(and_(Asset.kind == "doc", or_(Asset.category.is_(None), Asset.category != "download")))
                .order_by(Asset.uploaded_at.desc())
            )
            .all()
        )
        category_items: dict[str, list[Asset]] = {c.key: [] for c in doc_categories}
        for doc in docs:
            key = (doc.category or "").strip() or "other"
            if key == "download":
                continue
            if key not in category_items:
                key = "other" if "other" in category_items else key
            category_items.setdefault(key, []).append(doc)

        document_groups = [
            {"key": c.key, "title": c.title, "docs": category_items.get(c.key, [])}
            for c in doc_categories
            if category_items.get(c.key)
        ]

        hero_image = get_asset_by_slot("hero_image")
        hero_image_2 = get_asset_by_slot("hero_image_2")
        hero_image_3 = get_asset_by_slot("hero_image_3")
        hero_image_4 = get_asset_by_slot("hero_image_4")
        hero_image_5 = get_asset_by_slot("hero_image_5")
        product_image = get_asset_by_slot("product_image")
        registry_image = get_asset_by_slot("registry_image")
        feature_1_image = get_asset_by_slot("feature_1_image")
        feature_2_image = get_asset_by_slot("feature_2_image")
        feature_3_image = get_asset_by_slot("feature_3_image")
        feature_4_image = get_asset_by_slot("feature_4_image")
        adv_1_image = get_asset_by_slot("adv_1_image")
        adv_2_image = get_asset_by_slot("adv_2_image")
        adv_3_image = get_asset_by_slot("adv_3_image")
        adv_4_image = get_asset_by_slot("adv_4_image")
        adv_5_image = get_asset_by_slot("adv_5_image")
        adv_6_image = get_asset_by_slot("adv_6_image")
        features_image = get_asset_by_slot("features_image")
        turnstile_site_key = _turnstile_site_key() if turnstile_enabled() else ""
        support_submit_token = issue_submit_token("support")

        return render_template(
            "index.html",
            blocks=blocks,
            hero_image=hero_image,
            hero_image_2=hero_image_2,
            hero_image_3=hero_image_3,
            hero_image_4=hero_image_4,
            hero_image_5=hero_image_5,
            product_image=product_image,
            registry_image=registry_image,
            feature_1_image=feature_1_image,
            feature_2_image=feature_2_image,
            feature_3_image=feature_3_image,
            feature_4_image=feature_4_image,
            adv_1_image=adv_1_image,
            adv_2_image=adv_2_image,
            adv_3_image=adv_3_image,
            adv_4_image=adv_4_image,
            adv_5_image=adv_5_image,
            adv_6_image=adv_6_image,
            features_image=features_image,
            document_groups=document_groups,
            year=datetime.utcnow().year,
            turnstile_site_key=turnstile_site_key,
            support_submit_token=support_submit_token,
        )

    def _feature_page(slug: str, image_slot: str):
        blocks = get_blocks()
        return render_template(
            f"features/{slug}.html",
            blocks=blocks,
            logo_asset=get_asset_by_slot("site_logo"),
            favicon_asset=get_asset_by_slot("site_favicon"),
            safety_image=get_asset_by_slot("safety_image"),
            scalability_image=get_asset_by_slot("scalability_image"),
            monitoring_image=get_asset_by_slot("monitoring_image"),
            integration_image=get_asset_by_slot("integration_image"),
            reliability_image=get_asset_by_slot("reliability_image"),
            deployment_image=get_asset_by_slot("deployment_image"),
        )

    @app.get("/features/safety-control")
    def feature_safety():
        return _feature_page("safety-control", "safety_image")

    @app.get("/features/scalable-architecture")
    def feature_scalable():
        return _feature_page("scalable-architecture", "scalability_image")

    @app.get("/features/realtime-monitoring")
    def feature_monitoring():
        return _feature_page("realtime-monitoring", "monitoring_image")

    @app.get("/features/flexible-integration")
    def feature_integration():
        return _feature_page("flexible-integration", "integration_image")

    @app.get("/features/reliability-247")
    def feature_reliability():
        return _feature_page("reliability-247", "reliability_image")

    @app.get("/features/fast-deployment")
    def feature_deployment():
        return _feature_page("fast-deployment", "deployment_image")

    @app.post("/support")
    def support_submit():
        user = current_client()
        if user is None:
            flash("Отправка заявок доступна только зарегистрированным пользователям. Войдите или зарегистрируйтесь.", "warning")
            return redirect(url_for("login", next=url_for("index") + "#support"))
        ok, reason = consume_submit_token("support", request.form.get("submit_token") or "")
        if not ok:
            if reason == "too_fast":
                flash("Слишком часто. Подождите несколько секунд и попробуйте ещё раз.", "warning")
            else:
                flash("Форма уже была отправлена или устарела. Обновите страницу и попробуйте ещё раз.", "warning")
            return redirect(url_for("index") + "#support")
        name = (request.form.get("name") or "").strip()
        email_honeypot = (request.form.get("email") or "").strip()
        email = ""
        company = (request.form.get("company") or "").strip()
        phone = normalize_multivalue(request.form.get("phone") or "")
        telegram = normalize_multivalue(request.form.get("telegram") or "")
        whatsapp = normalize_multivalue(request.form.get("whatsapp") or "")
        anydesk_id = normalize_multivalue(request.form.get("anydesk_id") or "")
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()
        honeypot = (request.form.get("fax") or "").strip()
        turnstile_token = (request.form.get("cf-turnstile-response") or "").strip()

        if not message:
            flash("Сообщение не может быть пустым.", "danger")
            return redirect(url_for("index") + "#support")

        if honeypot:
            return ("", 204)
        if email_honeypot:
            return ("", 204)

        if turnstile_enabled():
            remote_ip = (
                (request.headers.get("CF-Connecting-IP") or "").strip()
                or (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or request.remote_addr
            )
            if not verify_turnstile(turnstile_token, remote_ip):
                flash("Подтвердите, что вы не робот.", "danger")
                return redirect(url_for("index") + "#support")

        if looks_like_bot_headers():
            flash("Запрос отклонён системой защиты.", "danger")
            return redirect(url_for("index") + "#support")

        msg = SupportMessage(
            user_id=user.id,
            name=user.username or name,
            email=email,
            company=user.company or company,
            phone=user.phone or phone,
            telegram=user.telegram or telegram,
            whatsapp=user.whatsapp or whatsapp,
            anydesk_id=anydesk_id,
            subject=subject,
            message=message,
            complaints="",
            staff_notes="",
            status="new",
            created_at=datetime.utcnow(),
        )
        db().add(msg)
        db().flush()
        log_user_event("support_submit", user.id, {"message_id": msg.id})

        files_note = (request.form.get("files_note") or "").strip()
        files = request.files.getlist("files")
        uploaded = 0
        for f in files:
            if f is None or not getattr(f, "filename", ""):
                continue
            try:
                stored, original, size_bytes = store_support_upload(f, msg.id)
            except Exception:
                flash("Не удалось сохранить файл.", "danger")
                return redirect(url_for("index") + "#support")
            db().add(
                SupportAttachment(
                    message_id=msg.id,
                    stored_filename=stored,
                    original_filename=original,
                    direction="from_client",
                    note=files_note,
                    size_bytes=size_bytes,
                    uploaded_at=datetime.utcnow(),
                )
            )
            uploaded += 1
        if uploaded:
            flash("Файлы прикреплены к заявке.", "success")
        flash("Заявка отправлена. Мы свяжемся с вами.", "success")
        return redirect(url_for("index") + "#support")

    @app.get("/files/<int:asset_id>")
    def download_file(asset_id: int):
        asset = db().get(Asset, asset_id)
        if asset is None or asset.kind != "doc":
            abort(404)
        if (asset.category or "") == "download" and current_client() is None:
            return redirect(url_for("login", next=request.path))
        return send_from_directory(
            UPLOAD_DIR,
            asset.stored_filename,
            as_attachment=True,
            download_name=asset.original_filename,
        )

    @app.get("/downloads")
    @client_login_required
    def downloads():
        rows = (
            db()
            .scalars(
                select(Asset)
                .where(and_(Asset.kind == "doc", Asset.category == "download"))
                .order_by(Asset.uploaded_at.desc())
            )
            .all()
        )
        return render_template("downloads.html", rows=rows)

    @app.get("/downloads/files/<int:asset_id>")
    @client_login_required
    def downloads_file(asset_id: int):
        asset = db().get(Asset, asset_id)
        if asset is None or asset.kind != "doc" or (asset.category or "") != "download":
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            asset.stored_filename,
            as_attachment=True,
            download_name=asset.original_filename,
        )

    @app.get("/register")
    def register():
        if current_client() is not None:
            return redirect(url_for("cabinet"))
        return render_template(
            "auth_register.html",
            turnstile_site_key=_turnstile_site_key() if turnstile_enabled() else "",
            submit_token=issue_submit_token("register"),
        )

    @app.post("/register")
    def register_post():
        if current_client() is not None:
            return redirect(url_for("cabinet"))
        ok, reason = consume_submit_token("register", request.form.get("submit_token") or "")
        if not ok:
            if reason == "too_fast":
                flash("Слишком часто. Подождите несколько секунд и попробуйте ещё раз.", "warning")
            else:
                flash("Форма уже была отправлена или устарела. Обновите страницу и попробуйте ещё раз.", "warning")
            return redirect(url_for("register", next=request.args.get("next")))
        honeypot = (request.form.get("fax") or "").strip()
        if honeypot:
            return ("", 204)
        turnstile_token = (request.form.get("cf-turnstile-response") or "").strip()
        if turnstile_enabled():
            if not verify_turnstile(turnstile_token, remote_ip()):
                flash("Подтвердите, что вы не робот.", "danger")
                return redirect(url_for("register", next=request.args.get("next")))
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        company = (request.form.get("company") or "").strip()
        phone = normalize_multivalue(request.form.get("phone") or "")
        telegram = normalize_multivalue(request.form.get("telegram") or "")
        whatsapp = normalize_multivalue(request.form.get("whatsapp") or "")
        if not username or len(password) < 8:
            flash("Укажите логин и пароль (минимум 8 символов).", "danger")
            return redirect(url_for("register", next=request.args.get("next")))
        if not telegram and not whatsapp:
            flash("Укажите Telegram или WhatsApp для обратной связи.", "danger")
            return redirect(url_for("register", next=request.args.get("next")))
        exists = db().scalar(select(User.id).where(func.lower(User.username) == username.lower()))
        if exists:
            flash("Пользователь с таким логином уже существует.", "danger")
            return redirect(url_for("register", next=request.args.get("next")))
        u = User(
            username=username,
            password_hash=generate_password_hash(password),
            company=company,
            phone=phone,
            telegram=telegram,
            whatsapp=whatsapp,
            created_at=datetime.utcnow(),
        )
        db().add(u)
        db().flush()
        session["user_id"] = u.id
        log_user_event("register", u.id, {"username": u.username})
        flash("Регистрация успешна.", "success")
        next_url = safe_next_url(request.args.get("next"))
        return redirect(next_url or url_for("cabinet"))

    @app.get("/login")
    def login():
        if current_client() is not None:
            return redirect(url_for("cabinet"))
        return render_template(
            "auth_login.html",
            turnstile_site_key=_turnstile_site_key() if turnstile_enabled() else "",
            submit_token=issue_submit_token("login"),
        )

    @app.post("/login")
    def login_post():
        if current_client() is not None:
            return redirect(url_for("cabinet"))
        ok, reason = consume_submit_token("login", request.form.get("submit_token") or "")
        if not ok:
            if reason == "too_fast":
                flash("Слишком часто. Подождите несколько секунд и попробуйте ещё раз.", "warning")
            else:
                flash("Форма уже была отправлена или устарела. Обновите страницу и попробуйте ещё раз.", "warning")
            return redirect(url_for("login", next=request.args.get("next")))
        honeypot = (request.form.get("fax") or "").strip()
        if honeypot:
            return ("", 204)
        turnstile_token = (request.form.get("cf-turnstile-response") or "").strip()
        if turnstile_enabled():
            if not verify_turnstile(turnstile_token, remote_ip()):
                flash("Подтвердите, что вы не робот.", "danger")
                return redirect(url_for("login", next=request.args.get("next")))
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        u = db().scalar(select(User).where(User.username == username))
        if u is None or not check_password_hash(u.password_hash, password):
            flash("Неверный логин или пароль.", "danger")
            return redirect(url_for("login", next=request.args.get("next")))
        session["user_id"] = u.id
        log_user_event("login", u.id, {"username": u.username})
        flash("Вход выполнен.", "success")
        next_url = safe_next_url(request.args.get("next"))
        return redirect(next_url or url_for("cabinet"))

    @app.get("/forgot-password")
    def forgot_password():
        blocks = get_blocks()
        return render_template(
            "forgot_password.html",
            blocks=blocks,
            turnstile_site_key=_turnstile_site_key() if turnstile_enabled() else "",
            submit_token=issue_submit_token("forgot_password"),
        )

    @app.post("/forgot-password")
    def forgot_password_post():
        if current_client() is not None:
            return redirect(url_for("cabinet"))
        ok, reason = consume_submit_token("forgot_password", request.form.get("submit_token") or "")
        if not ok:
            if reason == "too_fast":
                flash("Слишком часто. Подождите несколько секунд и попробуйте ещё раз.", "warning")
            else:
                flash("Форма уже была отправлена или устарела. Обновите страницу и попробуйте ещё раз.", "warning")
            return redirect(url_for("forgot_password"))

        name = (request.form.get("name") or "").strip()
        username = (request.form.get("username") or "").strip()
        company = (request.form.get("company") or "").strip()
        phone = normalize_multivalue(request.form.get("phone") or "")
        contact_email = (request.form.get("contact_email") or "").strip()
        telegram = normalize_multivalue(request.form.get("telegram") or "")
        whatsapp = normalize_multivalue(request.form.get("whatsapp") or "")
        comment = (request.form.get("comment") or "").strip()
        honeypot = (request.form.get("fax") or "").strip()
        turnstile_token = (request.form.get("cf-turnstile-response") or "").strip()

        if honeypot:
            return ("", 204)
        if turnstile_enabled():
            if not verify_turnstile(turnstile_token, remote_ip()):
                flash("Подтвердите, что вы не робот.", "danger")
                return redirect(url_for("forgot_password"))

        if not (username or company or phone or contact_email or telegram or whatsapp or comment):
            flash("Заполните хотя бы одно поле, чтобы мы могли восстановить доступ.", "danger")
            return redirect(url_for("forgot_password"))

        if not (phone or contact_email or telegram or whatsapp):
            flash("Укажите контакт для связи (телефон, email, Telegram или WhatsApp).", "danger")
            return redirect(url_for("forgot_password"))

        body_lines = [
            "Запрос на восстановление доступа.",
            "",
            f"Имя: {name or '—'}",
            f"Логин: {username or '—'}",
            f"Компания: {company or '—'}",
            f"Телефон(ы): {phone or '—'}",
            f"Email: {contact_email or '—'}",
            f"Telegram: {telegram or '—'}",
            f"WhatsApp: {whatsapp or '—'}",
        ]
        if comment:
            body_lines.extend(["", "Комментарий:", comment])

        db().add(
            SupportMessage(
                user_id=None,
                name=name,
                email=contact_email,
                company=company,
                phone=phone,
                telegram=telegram,
                whatsapp=whatsapp,
                anydesk_id="",
                subject="Восстановление доступа",
                message="\n".join(body_lines),
                complaints="",
                staff_notes="",
                status="new",
                created_at=datetime.utcnow(),
            )
        )
        flash("Запрос отправлен в техподдержку. Мы свяжемся с вами.", "success")
        return redirect(url_for("login"))

    @app.post("/logout")
    def logout():
        uid = session.pop("user_id", None)
        try:
            log_user_event("logout", int(uid) if uid else None, None)
        except ValueError:
            log_user_event("logout", None, None)
        flash("Вы вышли из личного кабинета.", "success")
        next_url = safe_next_url(request.args.get("next"))
        return redirect(next_url or url_for("index"))

    @app.get("/cabinet")
    @client_login_required
    def cabinet():
        user = current_client()
        messages = db().scalars(
            select(SupportMessage).where(SupportMessage.user_id == user.id).order_by(SupportMessage.created_at.desc())
        ).all()
        return render_template("cabinet.html", messages=messages)

    @app.get("/setup")
    def setup_get():
        if db().scalar(select(AdminUser.id).limit(1)) is not None:
            abort(404)
        return render_template("admin/setup.html")

    @app.post("/setup")
    def setup_post():
        if db().scalar(select(AdminUser.id).limit(1)) is not None:
            abort(404)
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or len(password) < 8:
            flash("Укажите логин и пароль (минимум 8 символов).", "danger")
            return redirect(url_for("setup_get"))
        user = AdminUser(username=username, password_hash=generate_password_hash(password))
        db().add(user)
        db().flush()
        session["admin_user_id"] = user.id
        flash("Администратор создан.", "success")
        return redirect(url_for("admin_dashboard"))

    @app.get("/admin/login")
    def admin_login():
        if current_user() is not None:
            return redirect(url_for("admin_dashboard"))
        return render_template("admin/login.html")

    @app.post("/admin/login")
    def admin_login_post():
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = db().scalar(select(AdminUser).where(AdminUser.username == username))
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Неверный логин или пароль.", "danger")
            return redirect(url_for("admin_login"))

        session["admin_user_id"] = user.id
        flash("Вход выполнен.", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("admin_dashboard"))

    @app.post("/admin/logout")
    @login_required
    def admin_logout():
        session.pop("admin_user_id", None)
        flash("Вы вышли из админки.", "info")
        return redirect(url_for("index"))

    @app.get("/admin")
    @login_required
    def admin_dashboard():
        ensure_defaults()
        new_count = db().scalar(
            select(func.count()).select_from(SupportMessage).where(SupportMessage.status == "new")
        )
        return render_template(
            "admin/dashboard.html",
            user=current_user(),
            new_messages=int(new_count or 0),
        )

    @app.get("/admin/content")
    @login_required
    def admin_content_list():
        ensure_defaults()
        hidden = {
            "brand_primary",
            "brand_secondary",
            "brand_full",
            "slogan",
            "contacts_phone",
            "contacts_email",
            "contacts_address",
            "requisites_company",
            "requisites_inn",
            "requisites_kpp",
            "requisites_ogrn",
            "requisites_address",
            "requisites_bank",
            "requisites_bik",
            "requisites_rs",
            "requisites_ks",
            "option_turnstile_enabled",
            "option_submit_min_interval_seconds",
        }
        blocks = (
            db()
            .scalars(select(ContentBlock).where(~ContentBlock.key.in_(hidden)).order_by(ContentBlock.key.asc()))
            .all()
        )
        blocks_by_key = {block.key: block for block in blocks}
        feature_panels = []
        for panel_id in range(1, 5):
            title_key = f"feature_{panel_id}_title"
            desc_key = f"feature_{panel_id}_desc"
            slot_key = f"feature_{panel_id}_image"
            feature_panels.append(
                {
                    "id": panel_id,
                    "title_block": blocks_by_key.get(title_key),
                    "desc_block": blocks_by_key.get(desc_key),
                    "slot_key": slot_key,
                    "image": get_asset_by_slot(slot_key),
                }
            )
        advantages_panels = []
        for panel_id in range(1, 7):
            title_key = f"adv_{panel_id}_title"
            desc_key = f"adv_{panel_id}_desc"
            slot_key = f"adv_{panel_id}_image"
            advantages_panels.append(
                {
                    "id": panel_id,
                    "title_block": blocks_by_key.get(title_key),
                    "desc_block": blocks_by_key.get(desc_key),
                    "slot_key": slot_key,
                    "image": get_asset_by_slot(slot_key),
                }
            )
        registry_blocks = {
            field["key"]: blocks_by_key.get(field["key"])
            for section in REGISTRY_EDITOR_SECTIONS
            for field in section["fields"]
        }
        matched: set[str] = set()
        matched.update(registry_blocks.keys())

        def pick(title: str, predicate: Callable[[str], bool]) -> dict[str, object]:
            items = [block for block in blocks if predicate(block.key)]
            matched.update([block.key for block in items])
            return {"title": title, "items": items}

        groups = [
            pick("Hero", lambda key: key.startswith("hero_")),
            pick(
                "Ключевые возможности",
                lambda key: key.startswith("features_")
                or key.startswith("feature_")
                or key.startswith("advantages_")
                or key.startswith("adv_"),
            ),
            pick("Документы", lambda key: key.startswith("documents_")),
            pick("Поддержка", lambda key: key.startswith("support_")),
        ]
        groups.append(
            {
                "title": "Другое",
                "items": [block for block in blocks if block.key not in matched],
            }
        )
        return render_template(
            "admin/content_list.html",
            groups=groups,
            feature_panels=feature_panels,
            advantages_panels=advantages_panels,
            registry_sections=REGISTRY_EDITOR_SECTIONS,
            registry_blocks=registry_blocks,
            registry_image=get_asset_by_slot("registry_image"),
        )

    @app.post("/admin/features-panels/<int:panel_id>")
    @login_required
    def admin_feature_panel_save(panel_id: int):
        ensure_defaults()
        if panel_id not in {1, 2, 3, 4}:
            abort(404)
        title_key = f"feature_{panel_id}_title"
        desc_key = f"feature_{panel_id}_desc"
        title_block = db().get(ContentBlock, title_key)
        desc_block = db().get(ContentBlock, desc_key)
        if title_block is None or desc_block is None:
            abort(404)
        title_block.body = (request.form.get("title") or "").strip()
        desc_block.body = request.form.get("desc") or ""
        flash("Панель обновлена.", "success")
        return redirect(url_for("admin_content_list") + "#feature-panels")

    @app.post("/admin/advantages-panels/<int:panel_id>")
    @login_required
    def admin_advantages_panel_save(panel_id: int):
        ensure_defaults()
        if panel_id not in {1, 2, 3, 4, 5, 6}:
            abort(404)
        title_key = f"adv_{panel_id}_title"
        desc_key = f"adv_{panel_id}_desc"
        title_block = db().get(ContentBlock, title_key)
        desc_block = db().get(ContentBlock, desc_key)
        if title_block is None or desc_block is None:
            abort(404)
        title_block.body = (request.form.get("title") or "").strip()
        desc_block.body = request.form.get("desc") or ""
        flash("Панель обновлена.", "success")
        return redirect(url_for("admin_content_list") + "#advantages-panels")

    @app.post("/admin/registry-content")
    @login_required
    def admin_registry_content_save():
        ensure_defaults()
        keys = [field["key"] for section in REGISTRY_EDITOR_SECTIONS for field in section["fields"]]
        for key in keys:
            block = db().get(ContentBlock, key)
            if block is None:
                continue
            value = request.form.get(key)
            if value is None:
                continue
            block.body = value.strip() if "\n" not in value else value
        flash("Блок реестра ПО обновлён.", "success")
        return redirect(url_for("admin_content_list") + "#registry-editor")

    @app.get("/admin/features")
    @login_required
    def admin_features_list():
        ensure_defaults()
        blocks = get_blocks()
        feature_pages = [
            {
                "slug": "safety-control",
                "title_key": "safety_title",
                "content_key": "safety_content",
                "image_slot": "safety_image",
                "label": "Безопасность и контроль",
            },
            {
                "slug": "scalable-architecture",
                "title_key": "scalability_title",
                "content_key": "scalability_content",
                "image_slot": "scalability_image",
                "label": "Масштабируемая архитектура",
            },
            {
                "slug": "realtime-monitoring",
                "title_key": "monitoring_title",
                "content_key": "monitoring_content",
                "image_slot": "monitoring_image",
                "label": "Регулярная готовность",
            },
            {
                "slug": "flexible-integration",
                "title_key": "integration_title",
                "content_key": "integration_content",
                "image_slot": "integration_image",
                "label": "Гибкая интеграция",
            },
            {
                "slug": "reliability-247",
                "title_key": "reliability_title",
                "content_key": "reliability_content",
                "image_slot": "reliability_image",
                "label": "Надёжность 24/7",
            },
            {
                "slug": "fast-deployment",
                "title_key": "deployment_title",
                "content_key": "deployment_content",
                "image_slot": "deployment_image",
                "label": "Быстрое внедрение",
            },
        ]
        for fp in feature_pages:
            fp["title_block"] = blocks.get(fp["title_key"])
            fp["content_block"] = blocks.get(fp["content_key"])
            fp["image"] = get_asset_by_slot(fp["image_slot"])
        return render_template("admin/features_list.html", feature_pages=feature_pages)

    @app.get("/admin/features/<string:slug>")
    @login_required
    def admin_features_edit(slug: str):
        ensure_defaults()
        blocks = get_blocks()
        feature_map = {
            "safety-control": {
                "prefix": "safety",
                "title_key": "safety_title",
                "content_key": "safety_content",
                "key_features_title_key": "safety_key_features_title",
                "key_features_body_key": "safety_key_features_body",
                "image_slot": "safety_image",
            },
            "scalable-architecture": {
                "prefix": "scalability",
                "title_key": "scalability_title",
                "content_key": "scalability_content",
                "key_features_title_key": "scalability_key_features_title",
                "key_features_body_key": "scalability_key_features_body",
                "image_slot": "scalability_image",
            },
            "realtime-monitoring": {
                "prefix": "monitoring",
                "title_key": "monitoring_title",
                "content_key": "monitoring_content",
                "key_features_title_key": "monitoring_key_features_title",
                "key_features_body_key": "monitoring_key_features_body",
                "image_slot": "monitoring_image",
            },
            "flexible-integration": {
                "prefix": "integration",
                "title_key": "integration_title",
                "content_key": "integration_content",
                "key_features_title_key": "integration_key_features_title",
                "key_features_body_key": "integration_key_features_body",
                "image_slot": "integration_image",
            },
            "reliability-247": {
                "prefix": "reliability",
                "title_key": "reliability_title",
                "content_key": "reliability_content",
                "key_features_title_key": "reliability_key_features_title",
                "key_features_body_key": "reliability_key_features_body",
                "image_slot": "reliability_image",
            },
            "fast-deployment": {
                "prefix": "deployment",
                "title_key": "deployment_title",
                "content_key": "deployment_content",
                "key_features_title_key": "deployment_key_features_title",
                "key_features_body_key": "deployment_key_features_body",
                "image_slot": "deployment_image",
            },
        }
        if slug not in feature_map:
            abort(404)
        info = feature_map[slug]
        return render_template(
            "admin/features_edit.html",
            slug=slug,
            blocks=blocks,
            key_features_prefix=info["prefix"],
            title_block=blocks.get(info["title_key"]),
            content_block=blocks.get(info["content_key"]),
            key_features_title_block=blocks.get(info["key_features_title_key"]),
            key_features_body_block=blocks.get(info["key_features_body_key"]),
            image=get_asset_by_slot(info["image_slot"]),
            image_slot=info["image_slot"],
        )

    @app.post("/admin/features/<string:slug>")
    @login_required
    def admin_features_save(slug: str):
        ensure_defaults()
        feature_map = {
            "safety-control": {
                "prefix": "safety",
                "title_key": "safety_title",
                "content_key": "safety_content",
                "key_features_title_key": "safety_key_features_title",
                "key_features_body_key": "safety_key_features_body",
            },
            "scalable-architecture": {
                "prefix": "scalability",
                "title_key": "scalability_title",
                "content_key": "scalability_content",
                "key_features_title_key": "scalability_key_features_title",
                "key_features_body_key": "scalability_key_features_body",
            },
            "realtime-monitoring": {
                "prefix": "monitoring",
                "title_key": "monitoring_title",
                "content_key": "monitoring_content",
                "key_features_title_key": "monitoring_key_features_title",
                "key_features_body_key": "monitoring_key_features_body",
            },
            "flexible-integration": {
                "prefix": "integration",
                "title_key": "integration_title",
                "content_key": "integration_content",
                "key_features_title_key": "integration_key_features_title",
                "key_features_body_key": "integration_key_features_body",
            },
            "reliability-247": {
                "prefix": "reliability",
                "title_key": "reliability_title",
                "content_key": "reliability_content",
                "key_features_title_key": "reliability_key_features_title",
                "key_features_body_key": "reliability_key_features_body",
            },
            "fast-deployment": {
                "prefix": "deployment",
                "title_key": "deployment_title",
                "content_key": "deployment_content",
                "key_features_title_key": "deployment_key_features_title",
                "key_features_body_key": "deployment_key_features_body",
            },
        }
        if slug not in feature_map:
            abort(404)
        info = feature_map[slug]
        title_block = db().get(ContentBlock, info["title_key"])
        content_block = db().get(ContentBlock, info["content_key"])
        key_features_title_block = db().get(ContentBlock, info["key_features_title_key"])
        key_features_body_block = db().get(ContentBlock, info["key_features_body_key"])
        if (
            title_block is None
            or content_block is None
            or key_features_title_block is None
            or key_features_body_block is None
        ):
            abort(404)
        title_block.body = (request.form.get("title") or "").strip()
        content_block.body = request.form.get("content") or ""
        key_features_title_block.body = (request.form.get("key_features_title") or "").strip()
        key_features_body_block.body = request.form.get("key_features_body") or ""
        prefix = info["prefix"]
        for idx in range(1, 5):
            icon_block = db().get(ContentBlock, f"{prefix}_kf_{idx}_icon")
            title_item_block = db().get(ContentBlock, f"{prefix}_kf_{idx}_title")
            desc_item_block = db().get(ContentBlock, f"{prefix}_kf_{idx}_desc")
            if icon_block is not None:
                icon_block.body = (request.form.get(f"kf_{idx}_icon") or "").strip()
            if title_item_block is not None:
                title_item_block.body = (request.form.get(f"kf_{idx}_title") or "").strip()
            if desc_item_block is not None:
                desc_item_block.body = (request.form.get(f"kf_{idx}_desc") or "").strip()
        flash("Страница возможностей обновлена.", "success")
        return redirect(url_for("admin_features_edit", slug=slug))

    @app.get("/admin/content/<string:key>")
    @login_required
    def admin_content_edit(key: str):
        ensure_defaults()
        block = db().get(ContentBlock, key)
        if block is None:
            abort(404)
        return render_template("admin/content_edit.html", block=block)

    @app.post("/admin/content/<string:key>")
    @login_required
    def admin_content_save(key: str):
        ensure_defaults()
        block = db().get(ContentBlock, key)
        if block is None:
            abort(404)
        block.title = (request.form.get("title") or "").strip()
        block.body = request.form.get("body") or ""
        flash("Текст обновлён.", "success")
        return redirect(url_for("admin_content_edit", key=key))

    @app.get("/admin/assets")
    @login_required
    def admin_assets():
        ensure_defaults()
        assets = db().scalars(select(Asset).order_by(Asset.uploaded_at.desc())).all()
        doc_categories = (
            db()
            .scalars(select(DocumentCategory).order_by(DocumentCategory.sort_order.asc(), DocumentCategory.title.asc()))
            .all()
        )
        return render_template("admin/assets.html", assets=assets, doc_categories=doc_categories)

    @app.post("/admin/assets/upload")
    @login_required
    def admin_assets_upload():
        next_url = safe_next_url(request.form.get("next"))
        kind = (request.form.get("kind") or "").strip()
        slot_key = (request.form.get("slot_key") or "").strip() or None
        category = (request.form.get("category") or "").strip() or None
        title = (request.form.get("title") or "").strip()
        description = request.form.get("description") or ""
        ensure_defaults()
        file = request.files.get("file")
        if file is None or not file.filename:
            flash("Файл не выбран.", "danger")
            return redirect(next_url or url_for("admin_assets"))

        if kind == "image":
            if not allowed_file(file.filename, ALLOWED_IMAGE_EXTS):
                flash("Недопустимый формат изображения.", "danger")
                return redirect(next_url or url_for("admin_assets"))
            if not slot_key:
                flash("Для изображения укажите слот (например: hero_image).", "danger")
                return redirect(next_url or url_for("admin_assets"))

            try:
                stored, original = store_upload(file, kind=kind)
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(next_url or url_for("admin_assets"))
            existing = db().scalar(select(Asset).where(Asset.slot_key == slot_key))
            if existing is not None:
                try:
                    (UPLOAD_DIR / existing.stored_filename).unlink(missing_ok=True)
                except OSError:
                    pass
                existing.kind = "image"
                existing.category = None
                existing.stored_filename = stored
                existing.original_filename = original
                existing.title = title
                existing.description = description
                existing.uploaded_at = datetime.utcnow()
                flash("Изображение заменено.", "success")
                return redirect(next_url or url_for("admin_assets"))

            db().add(
                Asset(
                    kind="image",
                    slot_key=slot_key,
                    category=None,
                    stored_filename=stored,
                    original_filename=original,
                    title=title,
                    description=description,
                    uploaded_at=datetime.utcnow(),
                )
            )
            flash("Изображение загружено.", "success")
            return redirect(next_url or url_for("admin_assets"))

        if kind == "doc":
            if not allowed_file(file.filename, ALLOWED_DOC_EXTS):
                flash("Недопустимый формат документа.", "danger")
                return redirect(next_url or url_for("admin_assets"))
            doc_category_keys = set(db().scalars(select(DocumentCategory.key)).all())
            normalized_category = (category or "").strip() or "other"
            if normalized_category == "download":
                flash("Категория download зарезервирована для «Дистрибутивов».", "danger")
                return redirect(next_url or url_for("admin_assets"))
            if normalized_category not in doc_category_keys:
                flash("Выберите существующую категорию документов.", "danger")
                return redirect(next_url or url_for("admin_assets"))
            try:
                stored, original = store_upload(file, kind=kind)
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(next_url or url_for("admin_assets"))
            db().add(
                Asset(
                    kind="doc",
                    slot_key=None,
                    category=normalized_category,
                    stored_filename=stored,
                    original_filename=original,
                    title=title,
                    description=description,
                    uploaded_at=datetime.utcnow(),
                )
            )
            flash("Документ загружен.", "success")
            return redirect(next_url or url_for("admin_assets"))

        flash("Выберите тип: image или doc.", "danger")
        return redirect(next_url or url_for("admin_assets"))

    @app.post("/admin/assets/delete/<int:asset_id>")
    @login_required
    def admin_assets_delete(asset_id: int):
        next_url = safe_next_url(request.form.get("next"))
        asset = db().get(Asset, asset_id)
        if asset is None:
            abort(404)
        try:
            (UPLOAD_DIR / asset.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
        db().delete(asset)
        flash("Файл удалён.", "info")
        return redirect(next_url or url_for("admin_assets"))

    @app.get("/admin/documents")
    @login_required
    def admin_documents():
        ensure_defaults()
        doc_categories = (
            db()
            .scalars(select(DocumentCategory).order_by(DocumentCategory.sort_order.asc(), DocumentCategory.title.asc()))
            .all()
        )
        rows = (
            db()
            .scalars(
                select(Asset)
                .where(and_(Asset.kind == "doc", or_(Asset.category.is_(None), Asset.category != "download")))
                .order_by(Asset.uploaded_at.desc())
            )
            .all()
        )
        category_items: dict[str, list[Asset]] = {c.key: [] for c in doc_categories}
        for doc in rows:
            key = (doc.category or "").strip() or "other"
            if key == "download":
                continue
            if key not in category_items:
                key = "other" if "other" in category_items else key
            category_items.setdefault(key, []).append(doc)
        grouped_rows = [
            {"key": c.key, "title": c.title, "items": category_items.get(c.key, [])}
            for c in doc_categories
            if category_items.get(c.key)
        ]
        return render_template(
            "admin/downloads.html",
            rows=rows,
            page_title="Документы",
            list_title="Загруженные документы",
            page_subtitle="Документы из этого раздела видны на сайте в секции «Документы».",
            open_href=url_for("index") + "#documents",
            open_label="Открыть «Документы»",
            upload_endpoint="admin_assets_upload",
            delete_endpoint="admin_assets_delete",
            file_endpoint="download_file",
            upload_category_enabled=True,
            list_category_enabled=False,
            doc_categories=doc_categories,
            categories_manage_enabled=True,
            categories_create_endpoint="admin_doc_category_create",
            categories_update_endpoint="admin_doc_category_update",
            categories_delete_endpoint="admin_doc_category_delete",
            grouped_enabled=True,
            grouped_rows=grouped_rows,
        )

    def _validate_doc_category_key(key: str) -> str | None:
        key = (key or "").strip().lower()
        if not key or len(key) > 32:
            return None
        if not re.fullmatch(r"[a-z0-9_-]+", key):
            return None
        if key == "download":
            return None
        return key

    @app.post("/admin/documents/categories/create")
    @login_required
    def admin_doc_category_create():
        next_url = safe_next_url(request.form.get("next"))
        ensure_defaults()
        key = _validate_doc_category_key(request.form.get("key") or "")
        title = (request.form.get("title") or "").strip()
        try:
            sort_order = int((request.form.get("sort_order") or "100").strip() or "100")
        except ValueError:
            sort_order = 100
        if key is None:
            flash("Неверный ключ категории. Разрешены латиница/цифры/\"_\"/\"-\", до 32 символов.", "danger")
            return redirect(next_url or url_for("admin_documents") + "#doc-categories")
        if not title:
            flash("Укажите название категории.", "danger")
            return redirect(next_url or url_for("admin_documents") + "#doc-categories")
        existing = db().get(DocumentCategory, key)
        if existing is not None:
            flash("Категория с таким ключом уже существует.", "danger")
            return redirect(next_url or url_for("admin_documents") + "#doc-categories")
        db().add(DocumentCategory(key=key, title=title, sort_order=sort_order))
        flash("Категория добавлена.", "success")
        return redirect(next_url or url_for("admin_documents") + "#doc-categories")

    @app.post("/admin/documents/categories/<string:key>/update")
    @login_required
    def admin_doc_category_update(key: str):
        next_url = safe_next_url(request.form.get("next"))
        ensure_defaults()
        cat = db().get(DocumentCategory, key)
        if cat is None:
            abort(404)
        cat.title = (request.form.get("title") or "").strip()
        try:
            cat.sort_order = int((request.form.get("sort_order") or str(cat.sort_order)).strip() or str(cat.sort_order))
        except ValueError:
            pass
        if not cat.title:
            flash("Название категории не может быть пустым.", "danger")
            return redirect(next_url or url_for("admin_documents") + "#doc-categories")
        flash("Категория обновлена.", "success")
        return redirect(next_url or url_for("admin_documents") + "#doc-categories")

    @app.post("/admin/documents/categories/<string:key>/delete")
    @login_required
    def admin_doc_category_delete(key: str):
        next_url = safe_next_url(request.form.get("next"))
        ensure_defaults()
        cat = db().get(DocumentCategory, key)
        if cat is None:
            abort(404)
        in_use = db().scalar(select(func.count()).select_from(Asset).where(and_(Asset.kind == "doc", Asset.category == key)))
        if in_use:
            flash("Нельзя удалить категорию: к ней привязаны документы.", "danger")
            return redirect(next_url or url_for("admin_documents") + "#doc-categories")
        db().delete(cat)
        flash("Категория удалена.", "info")
        return redirect(next_url or url_for("admin_documents") + "#doc-categories")

    @app.get("/admin/downloads")
    @login_required
    def admin_downloads():
        rows = (
            db()
            .scalars(
                select(Asset)
                .where(and_(Asset.kind == "doc", Asset.category == "download"))
                .order_by(Asset.uploaded_at.desc())
            )
            .all()
        )
        return render_template(
            "admin/downloads.html",
            rows=rows,
            page_title="Дистрибутивы",
            list_title="Дистрибутивы",
            page_subtitle="Файлы из этого раздела доступны для скачивания только зарегистрированным пользователям.",
            open_href=url_for("downloads"),
            open_label="Открыть «Загрузки»",
            upload_category_enabled=False,
            fixed_category="download",
            upload_endpoint="admin_downloads_upload",
            delete_endpoint="admin_downloads_delete",
            file_endpoint="admin_downloads_file",
            list_category_enabled=False,
        )

    @app.get("/admin/downloads/files/<int:asset_id>")
    @login_required
    def admin_downloads_file(asset_id: int):
        asset = db().get(Asset, asset_id)
        if asset is None or asset.kind != "doc" or (asset.category or "") != "download":
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            asset.stored_filename,
            as_attachment=True,
            download_name=asset.original_filename,
        )

    @app.post("/admin/downloads/upload")
    @login_required
    def admin_downloads_upload():
        next_url = safe_next_url(request.form.get("next"))
        title = (request.form.get("title") or "").strip()
        description = request.form.get("description") or ""
        file = request.files.get("file")
        if file is None or not file.filename:
            flash("Файл не выбран.", "danger")
            return redirect(next_url or url_for("admin_downloads"))
        if not allowed_file(file.filename, ALLOWED_DOC_EXTS):
            flash("Недопустимый формат документа.", "danger")
            return redirect(next_url or url_for("admin_downloads"))
        try:
            stored, original = store_upload(file, kind="doc")
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(next_url or url_for("admin_downloads"))
        db().add(
            Asset(
                kind="doc",
                slot_key=None,
                category="download",
                stored_filename=stored,
                original_filename=original,
                title=title,
                description=description,
                uploaded_at=datetime.utcnow(),
            )
        )
        flash("Файл для скачивания добавлен.", "success")
        return redirect(next_url or url_for("admin_downloads"))

    @app.post("/admin/downloads/delete/<int:asset_id>")
    @login_required
    def admin_downloads_delete(asset_id: int):
        next_url = safe_next_url(request.form.get("next"))
        asset = db().get(Asset, asset_id)
        if asset is None or asset.kind != "doc" or (asset.category or "") != "download":
            abort(404)
        try:
            (UPLOAD_DIR / asset.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
        db().delete(asset)
        flash("Файл удалён.", "info")
        return redirect(next_url or url_for("admin_downloads"))

    @app.get("/admin/messages")
    @login_required
    def admin_messages():
        q = (request.args.get("q") or "").strip()
        status_filter = (request.args.get("status") or "all").strip()
        sort = (request.args.get("sort") or "newest").strip()
        date_from = (request.args.get("date_from") or "").strip()
        date_to = (request.args.get("date_to") or "").strip()
        try:
            page = max(1, int(request.args.get("page") or "1"))
        except ValueError:
            page = 1
        per_page = 50

        criteria: list[object] = []
        if status_filter and status_filter != "all":
            criteria.append(SupportMessage.status == status_filter)
        dt_from = _parse_date(date_from)
        if dt_from is not None:
            criteria.append(SupportMessage.created_at >= dt_from)
        dt_to = _parse_date(date_to)
        if dt_to is not None:
            dt0 = dt_to.replace(hour=0, minute=0, second=0, microsecond=0)
            criteria.append(SupportMessage.created_at < dt0 + timedelta(days=1))
        search_conditions, fts_q = build_messages_query(q)
        criteria.extend(search_conditions)
        where_clause = and_(*criteria) if criteria else None

        status_counts_rows = db().execute(
            select(SupportMessage.status, func.count()).group_by(SupportMessage.status)
        ).all()
        status_counts = {row[0]: int(row[1] or 0) for row in status_counts_rows}

        count_stmt = select(func.count()).select_from(SupportMessage)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total = int(db().scalar(count_stmt) or 0)

        pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, pages)

        stmt = select(SupportMessage)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        if sort == "oldest":
            stmt = stmt.order_by(SupportMessage.created_at.asc())
        else:
            stmt = stmt.order_by(SupportMessage.created_at.desc())
        stmt = stmt.limit(per_page).offset((page - 1) * per_page)
        msgs = db().scalars(stmt).all()
        msg_ids = [m.id for m in msgs]

        worklog_counts: dict[int, int] = {}
        files_from_client_counts: dict[int, int] = {}
        files_to_client_counts: dict[int, int] = {}
        message_media_flags: dict[int, dict[str, bool]] = {}
        if msg_ids:
            worklog_counts = {
                int(r[0]): int(r[1] or 0)
                for r in db()
                .execute(
                    select(SupportWorkLog.message_id, func.count())
                    .where(SupportWorkLog.message_id.in_(msg_ids))
                    .group_by(SupportWorkLog.message_id)
                )
                .all()
            }
            att_rows = db().execute(
                select(SupportAttachment.message_id, SupportAttachment.direction, func.count())
                .where(SupportAttachment.message_id.in_(msg_ids))
                .group_by(SupportAttachment.message_id, SupportAttachment.direction)
            ).all()
            for mid, direction, cnt in att_rows:
                d = str(direction or "").strip() or "from_client"
                if d == "to_client":
                    files_to_client_counts[int(mid)] = int(cnt or 0)
                else:
                    files_from_client_counts[int(mid)] = int(cnt or 0)

            image_exts = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
            audio_exts = {"mp3", "wav", "ogg", "m4a"}
            video_exts = {"mp4", "mov", "webm", "avi"}

            for mid in msg_ids:
                message_media_flags[int(mid)] = {"image": False, "audio": False, "video": False, "file": False}

            def _apply_media_flags(mid: int, original_filename: str, stored_filename: str) -> None:
                flags = message_media_flags.setdefault(mid, {"image": False, "audio": False, "video": False, "file": False})
                original = (original_filename or "").strip().lower()
                stored = (stored_filename or "").strip().lower()
                ext = original.rsplit(".", 1)[1] if "." in original else ""
                if original.startswith("audio_"):
                    flags["audio"] = True
                elif original.startswith("video_"):
                    flags["video"] = True
                elif ext in image_exts:
                    flags["image"] = True
                elif ext in audio_exts:
                    flags["audio"] = True
                elif ext in video_exts:
                    flags["video"] = True
                else:
                    flags["file"] = True
                if stored.endswith(".zip"):
                    flags["file"] = True

            att_meta = db().execute(
                select(SupportAttachment.message_id, SupportAttachment.original_filename, SupportAttachment.stored_filename)
                .where(SupportAttachment.message_id.in_(msg_ids))
            ).all()
            for mid, original, stored in att_meta:
                _apply_media_flags(int(mid), str(original or ""), str(stored or ""))

            complaint_meta = db().execute(
                select(SupportComplaintMedia.message_id, SupportComplaintMedia.original_filename, SupportComplaintMedia.stored_filename)
                .where(SupportComplaintMedia.message_id.in_(msg_ids))
            ).all()
            for mid, original, stored in complaint_meta:
                _apply_media_flags(int(mid), str(original or ""), str(stored or ""))

            worklog_meta = db().execute(
                select(SupportWorkLog.message_id, SupportWorkLogMedia.original_filename, SupportWorkLogMedia.stored_filename)
                .join(SupportWorkLog, SupportWorkLog.id == SupportWorkLogMedia.work_log_id)
                .where(SupportWorkLog.message_id.in_(msg_ids))
            ).all()
            for mid, original, stored in worklog_meta:
                _apply_media_flags(int(mid), str(original or ""), str(stored or ""))

        highlights: dict[int, dict[str, str]] = {}
        if fts_q and msgs and app.config.get("SUPPORT_FTS_AVAILABLE"):
            placeholders = ", ".join([f":id{i}" for i in range(len(msg_ids))])
            params: dict[str, object] = {"fts_q": fts_q}
            params.update({f"id{i}": msg_ids[i] for i in range(len(msg_ids))})
            rows = db().execute(
                text(
                    "SELECT rowid AS id, "
                    "highlight(support_messages_fts, 7, '<mark>', '</mark>') AS subject_hl, "
                    "snippet(support_messages_fts, 8, '<mark>', '</mark>', '…', 18) AS message_hl "
                    "FROM support_messages_fts "
                    "WHERE support_messages_fts MATCH :fts_q "
                    f"AND rowid IN ({placeholders})"
                ),
                params,
            ).mappings().all()
            def _safe_mark_html(value: str) -> str:
                escaped = html.escape(value or "", quote=False)
                return escaped.replace("&lt;mark&gt;", "<mark>").replace("&lt;/mark&gt;", "</mark>")

            highlights = {
                int(r["id"]): {
                    "subject": _safe_mark_html(str(r.get("subject_hl") or "")),
                    "message": _safe_mark_html(str(r.get("message_hl") or "")),
                }
                for r in rows
            }

        return render_template(
            "admin/messages.html",
            messages=msgs,
            highlights=highlights,
            worklog_counts=worklog_counts,
            files_from_client_counts=files_from_client_counts,
            files_to_client_counts=files_to_client_counts,
            message_media_flags=message_media_flags,
            q=q,
            status_filter=status_filter,
            sort=sort,
            date_from=date_from,
            date_to=date_to,
            page=page,
            pages=pages,
            per_page=per_page,
            total=total,
            status_counts=status_counts,
        )

    @app.get("/admin/messages/<int:msg_id>")
    @login_required
    def admin_message_view(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        attachments = db().scalars(
            select(SupportAttachment)
            .where(SupportAttachment.message_id == msg_id)
            .order_by(SupportAttachment.uploaded_at.desc())
        ).all()
        work_logs = db().scalars(
            select(SupportWorkLog)
            .where(SupportWorkLog.message_id == msg_id)
            .order_by(SupportWorkLog.created_at.desc())
        ).all()
        complaint_media = db().scalars(
            select(SupportComplaintMedia)
            .where(SupportComplaintMedia.message_id == msg_id)
            .order_by(SupportComplaintMedia.uploaded_at.desc())
        ).all()
        worklog_media_by_log: dict[int, list[SupportWorkLogMedia]] = {}
        worklog_media_flags: dict[int, dict[str, bool]] = {}
        if work_logs:
            log_ids = [w.id for w in work_logs]
            for lid in log_ids:
                worklog_media_by_log[int(lid)] = []
                worklog_media_flags[int(lid)] = {"image": False, "audio": False, "video": False, "file": False}
            rows = db().scalars(
                select(SupportWorkLogMedia)
                .where(SupportWorkLogMedia.work_log_id.in_(log_ids))
                .order_by(SupportWorkLogMedia.uploaded_at.desc())
            ).all()
            image_exts = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}
            audio_exts = {"mp3", "wav", "ogg", "m4a"}
            video_exts = {"mp4", "mov", "webm", "avi"}
            for r in rows:
                lid = int(r.work_log_id)
                worklog_media_by_log.setdefault(lid, []).append(r)
                flags = worklog_media_flags.setdefault(lid, {"image": False, "audio": False, "video": False, "file": False})
                original = (r.original_filename or "").strip().lower()
                stored = (r.stored_filename or "").strip().lower()
                ext = original.rsplit(".", 1)[1] if "." in original else ""
                if original.startswith("audio_"):
                    flags["audio"] = True
                elif original.startswith("video_"):
                    flags["video"] = True
                elif ext in image_exts:
                    flags["image"] = True
                elif ext in audio_exts:
                    flags["audio"] = True
                elif ext in video_exts:
                    flags["video"] = True
                else:
                    flags["file"] = True
                if stored.endswith(".zip"):
                    flags["file"] = True
        next_url = safe_next_url(request.args.get("next")) or url_for("admin_messages")
        return render_template(
            "admin/message_view.html",
            msg=msg,
            attachments=attachments,
            work_logs=work_logs,
            complaint_media=complaint_media,
            worklog_media_by_log=worklog_media_by_log,
            worklog_media_flags=worklog_media_flags,
            next_url=next_url,
        )

    @app.post("/admin/messages/<int:msg_id>/status")
    @login_required
    def admin_message_status(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        status = (request.form.get("status") or "").strip()
        if status not in {"new", "in_progress", "done", "archived"}:
            abort(400)
        msg.status = status
        flash("Статус обновлён.", "success")
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        return redirect(next_url)

    @app.post("/admin/messages/<int:msg_id>/delete")
    @login_required
    def admin_message_delete(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        delete_support_attachments([msg_id])
        delete_support_complaint_media([msg_id])
        delete_support_work_logs([msg_id])
        db().delete(msg)
        flash("Заявка удалена.", "info")
        return redirect(next_url)

    @app.post("/admin/messages/<int:msg_id>/update")
    @login_required
    def admin_message_update(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()
        complaints = request.form.get("complaints") or ""
        status = (request.form.get("status") or msg.status).strip()
        if status not in {"new", "in_progress", "done", "archived"}:
            abort(400)
        if not message:
            flash("Сообщение не может быть пустым.", "danger")
            return redirect(next_url)
        msg.subject = subject
        msg.message = message
        msg.complaints = complaints
        msg.status = status
        flash("Заявка обновлена.", "success")
        return redirect(next_url)

    @app.post("/admin/messages/<int:msg_id>/worklogs")
    @login_required
    def admin_message_worklog_create(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Заполните блок работы с заявкой.", "warning")
            return redirect(next_url)
        user = current_user()
        author = user.username if user else ""
        db().add(
            SupportWorkLog(
                message_id=msg_id,
                author=author,
                body=body,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
        flash("Блок добавлен.", "success")
        return redirect(next_url)

    @app.post("/admin/messages/worklogs/<int:log_id>/update")
    @login_required
    def admin_message_worklog_update(log_id: int):
        log = db().get(SupportWorkLog, log_id)
        if log is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=log.message_id)
        body = (request.form.get("body") or "").strip()
        if not body:
            flash("Блок не может быть пустым.", "danger")
            return redirect(next_url)
        log.body = body
        log.updated_at = datetime.utcnow()
        flash("Блок обновлён.", "success")
        return redirect(next_url)

    def _download_name(original_filename: str, stored_filename: str) -> str:
        name = (original_filename or "attachment").strip() or "attachment"
        stored = (stored_filename or "").lower()
        if stored.endswith(".zip") and not name.lower().endswith(".zip"):
            return f"{name}.zip"
        return name

    @app.post("/admin/messages/worklogs/<int:log_id>/media")
    @login_required
    def admin_worklog_media_upload(log_id: int):
        log = db().get(SupportWorkLog, log_id)
        if log is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=log.message_id)
        comment = (request.form.get("comment") or "").strip()
        files = request.files.getlist("files")
        uploaded = 0
        for f in files:
            if f is None or not getattr(f, "filename", ""):
                continue
            try:
                stored, original, size_bytes = store_support_upload_in_dir(
                    f, Path("support") / "worklogs" / str(log_id)
                )
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(next_url)
            db().add(
                SupportWorkLogMedia(
                    work_log_id=log_id,
                    stored_filename=stored,
                    original_filename=original,
                    comment=comment,
                    size_bytes=size_bytes,
                    uploaded_at=datetime.utcnow(),
                )
            )
            uploaded += 1
        if uploaded:
            flash("Медиа прикреплено.", "success")
        else:
            flash("Файлы не выбраны.", "warning")
        return redirect(next_url)

    @app.post("/admin/worklogs/media/<int:media_id>/update")
    @login_required
    def admin_worklog_media_update(media_id: int):
        m = db().get(SupportWorkLogMedia, media_id)
        if m is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        m.comment = (request.form.get("comment") or "").strip()
        flash("Комментарий обновлён.", "success")
        return redirect(next_url)

    @app.post("/admin/worklogs/media/<int:media_id>/delete")
    @login_required
    def admin_worklog_media_delete(media_id: int):
        m = db().get(SupportWorkLogMedia, media_id)
        if m is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        try:
            (UPLOAD_DIR / m.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
        db().delete(m)
        flash("Файл удалён.", "info")
        return redirect(next_url)

    @app.get("/admin/worklogs/media/<int:media_id>/download")
    @login_required
    def admin_worklog_media_download(media_id: int):
        m = db().get(SupportWorkLogMedia, media_id)
        if m is None:
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            m.stored_filename,
            as_attachment=True,
            download_name=_download_name(m.original_filename, m.stored_filename),
        )

    @app.get("/admin/worklogs/media/<int:media_id>/view")
    @login_required
    def admin_worklog_media_view(media_id: int):
        m = db().get(SupportWorkLogMedia, media_id)
        if m is None:
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            m.stored_filename,
            as_attachment=False,
            download_name=_download_name(m.original_filename, m.stored_filename),
        )

    @app.post("/admin/messages/worklogs/<int:log_id>/delete")
    @login_required
    def admin_message_worklog_delete(log_id: int):
        log = db().get(SupportWorkLog, log_id)
        if log is None:
            abort(404)
        msg_id = log.message_id
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        delete_support_worklog_media([log_id])
        db().delete(log)
        flash("Блок удалён.", "info")
        return redirect(next_url)

    @app.post("/admin/messages/<int:msg_id>/client")
    @login_required
    def admin_message_client_update(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        if request.form.get("name") is not None:
            msg.name = (request.form.get("name") or "").strip()
        if request.form.get("email") is not None:
            msg.email = (request.form.get("email") or "").strip()
        if request.form.get("company") is not None:
            msg.company = (request.form.get("company") or "").strip()
        if request.form.get("phone") is not None:
            msg.phone = normalize_multivalue(request.form.get("phone") or "")
        if request.form.get("telegram") is not None:
            msg.telegram = normalize_multivalue(request.form.get("telegram") or "")
        if request.form.get("whatsapp") is not None:
            msg.whatsapp = normalize_multivalue(request.form.get("whatsapp") or "")
        if request.form.get("anydesk_id") is not None:
            msg.anydesk_id = normalize_multivalue(request.form.get("anydesk_id") or "")
        if request.form.get("complaints") is not None:
            msg.complaints = request.form.get("complaints") or ""
        flash("Данные клиента сохранены.", "success")
        return redirect(next_url)

    @app.post("/admin/messages/<int:msg_id>/complaints/media")
    @login_required
    def admin_complaint_media_upload(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        comment = (request.form.get("comment") or "").strip()
        files = request.files.getlist("files")
        uploaded = 0
        for f in files:
            if f is None or not getattr(f, "filename", ""):
                continue
            try:
                stored, original, size_bytes = store_support_upload_in_dir(
                    f, Path("support") / "complaints" / str(msg_id)
                )
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(next_url)
            db().add(
                SupportComplaintMedia(
                    message_id=msg_id,
                    stored_filename=stored,
                    original_filename=original,
                    comment=comment,
                    size_bytes=size_bytes,
                    uploaded_at=datetime.utcnow(),
                )
            )
            uploaded += 1
        if uploaded:
            flash("Медиа прикреплено.", "success")
        else:
            flash("Файлы не выбраны.", "warning")
        return redirect(next_url)

    @app.post("/admin/complaints/media/<int:media_id>/update")
    @login_required
    def admin_complaint_media_update(media_id: int):
        m = db().get(SupportComplaintMedia, media_id)
        if m is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        m.comment = (request.form.get("comment") or "").strip()
        flash("Комментарий обновлён.", "success")
        return redirect(next_url)

    @app.post("/admin/complaints/media/<int:media_id>/delete")
    @login_required
    def admin_complaint_media_delete(media_id: int):
        m = db().get(SupportComplaintMedia, media_id)
        if m is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        try:
            (UPLOAD_DIR / m.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
        db().delete(m)
        flash("Файл удалён.", "info")
        return redirect(next_url)

    @app.get("/admin/complaints/media/<int:media_id>/download")
    @login_required
    def admin_complaint_media_download(media_id: int):
        m = db().get(SupportComplaintMedia, media_id)
        if m is None:
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            m.stored_filename,
            as_attachment=True,
            download_name=_download_name(m.original_filename, m.stored_filename),
        )

    @app.get("/admin/complaints/media/<int:media_id>/view")
    @login_required
    def admin_complaint_media_view(media_id: int):
        m = db().get(SupportComplaintMedia, media_id)
        if m is None:
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            m.stored_filename,
            as_attachment=False,
            download_name=_download_name(m.original_filename, m.stored_filename),
        )

    @app.post("/admin/messages/<int:msg_id>/upload")
    @login_required
    def admin_message_upload(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_message_view", msg_id=msg_id)
        files = request.files.getlist("files")
        note = (request.form.get("note") or "").strip()
        direction = (request.form.get("direction") or "from_client").strip()
        if direction not in {"from_client", "to_client"}:
            abort(400)
        uploaded = 0
        for f in files:
            if f is None or not getattr(f, "filename", ""):
                continue
            try:
                stored, original, size_bytes = store_support_upload(f, msg_id=msg_id)
            except ValueError as exc:
                flash(str(exc), "danger")
                return redirect(next_url)
            db().add(
                SupportAttachment(
                    message_id=msg_id,
                    stored_filename=stored,
                    original_filename=original,
                    direction=direction,
                    note=note,
                    size_bytes=size_bytes,
                    uploaded_at=datetime.utcnow(),
                )
            )
            uploaded += 1
        if uploaded:
            flash("Файлы загружены.", "success")
        else:
            flash("Файлы не выбраны.", "warning")
        return redirect(next_url)

    @app.get("/admin/messages/attachments/<int:att_id>")
    @login_required
    def admin_message_attachment_download(att_id: int):
        att = db().get(SupportAttachment, att_id)
        if att is None:
            abort(404)
        download_name = att.original_filename or "attachment"
        if (att.stored_filename or "").lower().endswith(".zip") and not download_name.lower().endswith(".zip"):
            download_name = f"{download_name}.zip"
        return send_from_directory(
            UPLOAD_DIR,
            att.stored_filename,
            as_attachment=True,
            download_name=download_name,
        )

    @app.post("/admin/messages/attachments/<int:att_id>/delete")
    @login_required
    def admin_message_attachment_delete(att_id: int):
        att = db().get(SupportAttachment, att_id)
        if att is None:
            abort(404)
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        try:
            (UPLOAD_DIR / att.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
        db().delete(att)
        flash("Файл удалён.", "info")
        return redirect(next_url)

    @app.post("/admin/messages/bulk")
    @login_required
    def admin_messages_bulk():
        ids_raw = request.form.getlist("ids")
        try:
            ids = [int(x) for x in ids_raw if str(x).strip()]
        except ValueError:
            abort(400)
        action = (request.form.get("action") or "").strip()
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")

        if not ids:
            flash("Выберите заявки.", "warning")
            return redirect(next_url)

        if action in {"new", "in_progress", "done", "archived"}:
            db().execute(
                update(SupportMessage)
                .where(SupportMessage.id.in_(ids))
                .values(status=action)
            )
            flash("Статусы обновлены.", "success")
            return redirect(next_url)

        if action == "delete":
            delete_support_attachments(ids)
            delete_support_complaint_media(ids)
            delete_support_work_logs(ids)
            db().execute(delete(SupportMessage).where(SupportMessage.id.in_(ids)))
            flash("Заявки удалены.", "info")
            return redirect(next_url)

        abort(400)

    @app.post("/admin/messages/create")
    @login_required
    def admin_message_create():
        next_url = safe_next_url(request.form.get("next")) or url_for("admin_messages")
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        company = (request.form.get("company") or "").strip()
        phone = normalize_multivalue(request.form.get("phone") or "")
        telegram = normalize_multivalue(request.form.get("telegram") or "")
        whatsapp = normalize_multivalue(request.form.get("whatsapp") or "")
        anydesk_id = normalize_multivalue(request.form.get("anydesk_id") or "")
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()
        complaints = request.form.get("complaints") or ""
        worklog_body = (request.form.get("worklog_body") or "").strip()
        status = (request.form.get("status") or "new").strip()
        if status not in {"new", "in_progress", "done", "archived"}:
            abort(400)

        if not message:
            flash("Сообщение не может быть пустым.", "danger")
            return redirect(next_url)

        msg = SupportMessage(
            name=name,
            email=email,
            company=company,
            phone=phone,
            telegram=telegram,
            whatsapp=whatsapp,
            anydesk_id=anydesk_id,
            subject=subject,
            message=message,
            complaints=complaints,
            staff_notes="",
            status=status,
            created_at=datetime.utcnow(),
        )
        db().add(msg)
        db().flush()
        if worklog_body:
            user = current_user()
            author = user.username if user else ""
            db().add(
                SupportWorkLog(
                    message_id=msg.id,
                    author=author,
                    body=worklog_body,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )
        flash("Заявка создана.", "success")
        return redirect(url_for("admin_message_view", msg_id=msg.id, next=next_url))

    @app.get("/admin/settings")
    @login_required
    def admin_settings():
        blocks = get_blocks()
        tab = (request.args.get("tab") or "branding").strip().lower()
        if tab not in {"branding", "password", "requisites", "contact", "options"}:
            tab = "branding"
        submit_min_interval_source = ""
        if (os.environ.get("GUARDE_SUBMIT_MIN_INTERVAL_SECONDS") or "").strip():
            submit_min_interval_source = "GUARDE_SUBMIT_MIN_INTERVAL_SECONDS"
        elif (os.environ.get("SUBMIT_MIN_INTERVAL_SECONDS") or "").strip():
            submit_min_interval_source = "SUBMIT_MIN_INTERVAL_SECONDS"
        elif (blocks.get("option_submit_min_interval_seconds") and (blocks["option_submit_min_interval_seconds"].body or "").strip()):
            submit_min_interval_source = "DB"
        turnstile_option_raw = (blocks.get("option_turnstile_enabled").body if blocks.get("option_turnstile_enabled") else "").strip().lower()
        turnstile_option_enabled = (not turnstile_option_raw) or (turnstile_option_raw in {"1", "true", "yes", "y", "on"})
        return render_template(
            "admin/settings.html",
            blocks=blocks,
            tab=tab,
            admin_user=current_user(),
            turnstile_site_configured=bool(_turnstile_site_key()),
            turnstile_secret_configured=bool(_turnstile_secret_key()),
            turnstile_option_enabled=turnstile_option_enabled,
            turnstile_effective_enabled=turnstile_enabled(),
            submit_min_interval_seconds=submit_min_interval_seconds(),
            submit_min_interval_source=submit_min_interval_source,
        )

    @app.post("/admin/settings/password")
    @login_required
    def admin_settings_password():
        next_url = safe_next_url(request.form.get("next"))
        user = current_user()
        if user is None:
            abort(401)
        current = request.form.get("current_password") or ""
        if not check_password_hash(user.password_hash, current):
            flash("Текущий пароль неверный.", "danger")
            return redirect(next_url or url_for("admin_settings", tab="password") + "#password")

        changed = False

        new_username = (request.form.get("new_username") or "").strip()
        if not new_username:
            new_username = user.username
        if new_username != user.username:
            exists = db().scalar(
                select(AdminUser.id).where(
                    func.lower(AdminUser.username) == new_username.lower(),
                    AdminUser.id != user.id,
                )
            )
            if exists:
                flash("Такой логин уже занят.", "danger")
                return redirect(next_url or url_for("admin_settings", tab="password") + "#password")
            if len(new_username) > 64:
                flash("Логин слишком длинный.", "danger")
                return redirect(next_url or url_for("admin_settings", tab="password") + "#password")
            user.username = new_username
            changed = True

        new_password = request.form.get("new_password") or ""
        if new_password:
            if len(new_password) < 8:
                flash("Новый пароль должен быть минимум 8 символов.", "danger")
                return redirect(next_url or url_for("admin_settings", tab="password") + "#password")
            user.password_hash = generate_password_hash(new_password)
            changed = True

        if changed:
            flash("Данные аккаунта обновлены.", "success")
        else:
            flash("Нечего менять.", "info")
        return redirect(next_url or url_for("admin_settings", tab="password") + "#password")

    @app.post("/admin/settings/branding")
    @login_required
    def admin_settings_branding():
        ensure_defaults()
        next_url = safe_next_url(request.form.get("next"))
        brand_full = db().get(ContentBlock, "brand_full")
        slogan = db().get(ContentBlock, "slogan")
        if brand_full is None or slogan is None:
            abort(404)
        brand_full.body = (request.form.get("brand_full") or "").strip()
        slogan.body = (request.form.get("slogan") or "").strip()
        flash("Брендинг обновлён.", "success")
        return redirect(next_url or url_for("admin_settings", tab="branding") + "#branding")

    @app.post("/admin/settings/requisites")
    @login_required
    def admin_settings_requisites():
        ensure_defaults()
        next_url = safe_next_url(request.form.get("next"))
        keys = [
            "requisites_company",
            "requisites_inn",
            "requisites_kpp",
            "requisites_ogrn",
            "requisites_address",
            "requisites_bank",
            "requisites_bik",
            "requisites_rs",
            "requisites_ks",
        ]
        for key in keys:
            block = db().get(ContentBlock, key)
            if block is None:
                continue
            block.body = (request.form.get(key) or "").strip()
        flash("Реквизиты обновлены.", "success")
        return redirect(next_url or url_for("admin_settings", tab="requisites") + "#requisites")

    @app.post("/admin/settings/contact")
    @login_required
    def admin_settings_contact():
        ensure_defaults()
        next_url = safe_next_url(request.form.get("next"))
        keys = ["contacts_phone", "contacts_email", "contacts_address"]
        for key in keys:
            block = db().get(ContentBlock, key)
            if block is None:
                continue
            raw = request.form.get(key) or ""
            if key in {"contacts_phone", "contacts_email"}:
                block.body = normalize_multivalue(raw)
            else:
                block.body = raw.strip()
        flash("Контакты обновлены.", "success")
        return redirect(next_url or url_for("admin_settings", tab="contact") + "#contact")

    @app.post("/admin/settings/admin-contact")
    @login_required
    def admin_settings_admin_contact():
        next_url = safe_next_url(request.form.get("next"))
        user = current_user()
        if user is None:
            abort(401)
        user.first_name = (request.form.get("admin_first_name") or "").strip()
        user.last_name = (request.form.get("admin_last_name") or "").strip()
        user.phone = normalize_multivalue(request.form.get("admin_phone") or "")
        user.email = normalize_multivalue(request.form.get("admin_email") or "")
        user.telegram = normalize_multivalue(request.form.get("admin_telegram") or "")
        user.whatsapp = normalize_multivalue(request.form.get("admin_whatsapp") or "")
        flash("Контакты администратора обновлены.", "success")
        return redirect(next_url or url_for("admin_settings", tab="contact") + "#contact")

    @app.post("/admin/settings/options")
    @login_required
    def admin_settings_options():
        ensure_defaults()
        next_url = safe_next_url(request.form.get("next"))
        raw_interval = (request.form.get("option_submit_min_interval_seconds") or "").strip()
        try:
            interval = int(raw_interval)
        except ValueError:
            interval = 8
        if interval < 0:
            interval = 0
        if interval > 300:
            interval = 300
        interval_block = db().get(ContentBlock, "option_submit_min_interval_seconds")
        if interval_block is not None:
            interval_block.body = str(interval)
        turnstile_block = db().get(ContentBlock, "option_turnstile_enabled")
        if turnstile_block is not None:
            turnstile_block.body = "1" if request.form.get("option_turnstile_enabled") else "0"
        flash("Опции обновлены.", "success")
        return redirect(next_url or url_for("admin_settings", tab="options") + "#options")

    @app.get("/admin/logs/users")
    @login_required
    def admin_logs_users():
        q = (request.args.get("q") or "").strip()
        event = (request.args.get("event") or "all").strip()
        date_from = (request.args.get("date_from") or "").strip()
        date_to = (request.args.get("date_to") or "").strip()
        try:
            page = max(1, int(request.args.get("page") or "1"))
        except ValueError:
            page = 1
        per_page = 100

        criteria: list[object] = []
        if event and event != "all":
            criteria.append(UserEventLog.event == event)
        dt_from = _parse_date(date_from)
        if dt_from is not None:
            criteria.append(UserEventLog.created_at >= dt_from)
        dt_to = _parse_date(date_to)
        if dt_to is not None:
            dt0 = dt_to.replace(hour=0, minute=0, second=0, microsecond=0)
            criteria.append(UserEventLog.created_at < dt0 + timedelta(days=1))
        if q:
            user_ids_like = db().scalars(select(User.id).where(_messages_ci_like(User.username, q))).all()
            crit = [
                _messages_ci_like(UserEventLog.details, q),
                _messages_ci_like(UserEventLog.ip, q),
                _messages_ci_like(UserEventLog.user_agent, q),
            ]
            if user_ids_like:
                crit.append(UserEventLog.user_id.in_([int(x) for x in user_ids_like]))
            criteria.append(or_(*crit))
        where_clause = and_(*criteria) if criteria else None

        event_counts_rows = db().execute(select(UserEventLog.event, func.count()).group_by(UserEventLog.event)).all()
        event_counts = {str(e or ""): int(c or 0) for e, c in event_counts_rows}

        count_stmt = select(func.count()).select_from(UserEventLog)
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total = int(db().scalar(count_stmt) or 0)
        pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, pages)

        stmt = select(UserEventLog)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        stmt = stmt.order_by(UserEventLog.created_at.desc()).limit(per_page).offset((page - 1) * per_page)
        rows = db().scalars(stmt).all()

        user_ids = sorted({int(r.user_id) for r in rows if r.user_id is not None})
        users_map: dict[int, str] = {}
        if user_ids:
            users_map = {int(uid): uname for uid, uname in db().execute(select(User.id, User.username).where(User.id.in_(user_ids))).all()}

        return render_template(
            "admin/log_users.html",
            rows=rows,
            users_map=users_map,
            q=q,
            event=event,
            event_counts=event_counts,
            date_from=date_from,
            date_to=date_to,
            page=page,
            pages=pages,
            total=total,
        )

    @app.get("/admin/logs/password-resets")
    @login_required
    def admin_logs_password_resets():
        q = (request.args.get("q") or "").strip()
        date_from = (request.args.get("date_from") or "").strip()
        date_to = (request.args.get("date_to") or "").strip()
        try:
            page = max(1, int(request.args.get("page") or "1"))
        except ValueError:
            page = 1
        per_page = 100

        criteria: list[object] = [SupportMessage.subject == "Восстановление доступа"]
        dt_from = _parse_date(date_from)
        if dt_from is not None:
            criteria.append(SupportMessage.created_at >= dt_from)
        dt_to = _parse_date(date_to)
        if dt_to is not None:
            dt0 = dt_to.replace(hour=0, minute=0, second=0, microsecond=0)
            criteria.append(SupportMessage.created_at < dt0 + timedelta(days=1))
        if q:
            criteria.append(
                or_(
                    _messages_ci_like(SupportMessage.name, q),
                    _messages_ci_like(SupportMessage.email, q),
                    _messages_ci_like(SupportMessage.company, q),
                    _messages_ci_like(SupportMessage.phone, q),
                    _messages_ci_like(SupportMessage.telegram, q),
                    _messages_ci_like(SupportMessage.whatsapp, q),
                    _messages_ci_like(SupportMessage.message, q),
                )
            )

        where_clause = and_(*criteria)
        total = int(db().scalar(select(func.count()).select_from(SupportMessage).where(where_clause)) or 0)
        pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, pages)

        rows = db().scalars(
            select(SupportMessage)
            .where(where_clause)
            .order_by(SupportMessage.created_at.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
        ).all()

        return render_template(
            "admin/log_password_resets.html",
            rows=rows,
            q=q,
            date_from=date_from,
            date_to=date_to,
            page=page,
            pages=pages,
            total=total,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
