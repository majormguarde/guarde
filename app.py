from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
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

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from models import AdminUser, Asset, Base, ContentBlock, SupportMessage


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "site.db"
UPLOAD_DIR = APP_DIR / "static" / "uploads"

ALLOWED_IMAGE_EXTS = {"png", "jpg", "jpeg", "webp", "svg", "ico"}
ALLOWED_DOC_EXTS = {"pdf", "doc", "docx", "xls", "xlsx", "zip", "rar"}

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
    "contacts_phone": {"title": "Контакты — телефон", "body": "+7 (495) 123-45-67"},
    "contacts_email": {"title": "Контакты — e-mail", "body": "support@strazh-avangard.ru"},
    "contacts_address": {"title": "Контакты — адрес", "body": "г. Москва, Инновационный проезд, д. 1"},
}


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        columns = {r._mapping["name"] for r in conn.execute(text("PRAGMA table_info(support_messages)"))}
        if "company" not in columns:
            conn.execute(
                text(
                    "ALTER TABLE support_messages "
                    "ADD COLUMN company VARCHAR(200) NOT NULL DEFAULT ''"
                )
            )

    @app.before_request
    def _open_db() -> None:
        g.db = SessionLocal()

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

        if created:
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

    def store_upload(file_storage, kind: str) -> tuple[str, str]:
        original_name = file_storage.filename or ""
        safe = secure_filename(original_name)
        if not safe:
            abort(400)
        ext = safe.rsplit(".", 1)[1].lower()
        stored = f"{uuid.uuid4().hex}.{ext}"
        file_storage.save(UPLOAD_DIR / stored)
        return stored, original_name

    @app.get("/uploads/<path:filename>")
    def uploads(filename: str):
        return send_from_directory(UPLOAD_DIR, filename)

    @app.get("/favicon.ico")
    def favicon():
        asset = get_asset_by_slot("site_favicon")
        if asset is None:
            abort(404)
        return send_from_directory(UPLOAD_DIR, asset.stored_filename)

    @app.get("/")
    def index():
        blocks = get_blocks()
        docs = db().scalars(select(Asset).where(Asset.kind == "doc").order_by(Asset.uploaded_at.desc())).all()
        prices = [d for d in docs if (d.category or "") == "price"]
        registry_docs = [d for d in docs if (d.category or "") == "registry"]
        other_docs = [d for d in docs if (d.category or "") not in {"price", "registry"}]

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
        features_image = get_asset_by_slot("features_image")

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
            features_image=features_image,
            prices=prices,
            registry_docs=registry_docs,
            other_docs=other_docs,
            year=datetime.utcnow().year,
        )

    @app.post("/support")
    def support_submit():
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        company = (request.form.get("company") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()

        if not message:
            flash("Сообщение не может быть пустым.", "danger")
            return redirect(url_for("index") + "#support")

        db().add(
            SupportMessage(
                name=name,
                email=email,
                company=company,
                phone=phone,
                subject=subject,
                message=message,
                status="new",
                created_at=datetime.utcnow(),
            )
        )
        flash("Заявка отправлена. Мы свяжемся с вами.", "success")
        return redirect(url_for("index") + "#support")

    @app.get("/files/<int:asset_id>")
    def download_file(asset_id: int):
        asset = db().get(Asset, asset_id)
        if asset is None or asset.kind != "doc":
            abort(404)
        return send_from_directory(
            UPLOAD_DIR,
            asset.stored_filename,
            as_attachment=True,
            download_name=asset.original_filename,
        )

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
        hidden = {"brand_primary", "brand_secondary"}
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
        matched: set[str] = set()

        def pick(title: str, predicate: Callable[[str], bool]) -> dict[str, object]:
            items = [block for block in blocks if predicate(block.key)]
            matched.update([block.key for block in items])
            return {"title": title, "items": items}

        groups = [
            pick("Брендинг", lambda key: key in {"brand_full", "slogan"}),
            pick("Hero", lambda key: key.startswith("hero_")),
            pick("Реестр ПО", lambda key: key.startswith("registry_")),
            pick(
                "Ключевые возможности",
                lambda key: key.startswith("features_")
                or key.startswith("feature_")
                or key.startswith("advantages_")
                or key.startswith("adv_"),
            ),
            pick("Документы", lambda key: key.startswith("documents_")),
            pick("Поддержка", lambda key: key.startswith("support_")),
            pick("Контакты", lambda key: key.startswith("contacts_")),
        ]
        groups.append(
            {
                "title": "Другое",
                "items": [block for block in blocks if block.key not in matched],
            }
        )
        return render_template("admin/content_list.html", groups=groups, feature_panels=feature_panels)

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
        assets = db().scalars(select(Asset).order_by(Asset.uploaded_at.desc())).all()
        return render_template("admin/assets.html", assets=assets)

    @app.post("/admin/assets/upload")
    @login_required
    def admin_assets_upload():
        next_url = safe_next_url(request.form.get("next"))
        kind = (request.form.get("kind") or "").strip()
        slot_key = (request.form.get("slot_key") or "").strip() or None
        category = (request.form.get("category") or "").strip() or None
        title = (request.form.get("title") or "").strip()
        description = request.form.get("description") or ""
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

            stored, original = store_upload(file, kind=kind)
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
            stored, original = store_upload(file, kind=kind)
            db().add(
                Asset(
                    kind="doc",
                    slot_key=None,
                    category=category or "other",
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

    @app.get("/admin/messages")
    @login_required
    def admin_messages():
        msgs = db().scalars(select(SupportMessage).order_by(SupportMessage.created_at.desc())).all()
        return render_template("admin/messages.html", messages=msgs)

    @app.get("/admin/messages/<int:msg_id>")
    @login_required
    def admin_message_view(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        return render_template("admin/message_view.html", msg=msg)

    @app.post("/admin/messages/<int:msg_id>/status")
    @login_required
    def admin_message_status(msg_id: int):
        msg = db().get(SupportMessage, msg_id)
        if msg is None:
            abort(404)
        status = (request.form.get("status") or "").strip()
        if status not in {"new", "in_progress", "done"}:
            abort(400)
        msg.status = status
        flash("Статус обновлён.", "success")
        return redirect(url_for("admin_message_view", msg_id=msg_id))

    @app.get("/admin/settings")
    @login_required
    def admin_settings():
        blocks = get_blocks()
        return render_template("admin/settings.html", blocks=blocks)

    @app.post("/admin/settings/password")
    @login_required
    def admin_settings_password():
        user = current_user()
        if user is None:
            abort(401)
        current = request.form.get("current_password") or ""
        new = request.form.get("new_password") or ""
        if not check_password_hash(user.password_hash, current):
            flash("Текущий пароль неверный.", "danger")
            return redirect(url_for("admin_settings"))
        if len(new) < 8:
            flash("Новый пароль должен быть минимум 8 символов.", "danger")
            return redirect(url_for("admin_settings"))
        user.password_hash = generate_password_hash(new)
        flash("Пароль обновлён.", "success")
        return redirect(url_for("admin_settings"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
