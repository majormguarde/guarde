import React, { useState } from 'react';
import {
  Shield, Lock, Users, Clock, FileText, Download,
  Settings, Server, CheckCircle, Mail, Phone,
  ChevronRight, LayoutDashboard, MessageSquare, Image as ImageIcon,
  Save, X, Plus, Trash2
} from 'lucide-react';

// --- Исходные данные сайта ---
const initialData = {
  hero: {
    title: "Сетевая СКУД «Стражъ | Авангардъ»",
    subtitle: "Российская система контроля и управления доступом. Надежная защита периметра, учет рабочего времени и интеграция с корпоративными системами.",
    imageUrl: "https://images.unsplash.com/photo-1557597774-9d273605dfa9?auto=format&fit=crop&q=80&w=2000",
  },
  registry: {
    title: "Включено в Единый реестр российских программ",
    description: "Программный комплекс «Стражъ | Авангардъ» официально зарегистрирован в реестре Минцифры РФ (№ 12345 от 15.05.2023). Идеально подходит для импортозамещения на объектах КИИ и в государственных структурах.",
  },
  features: [
    { id: 1, title: "Биометрический доступ", description: "Распознавание лиц и отпечатков пальцев за 0.3 секунды.", icon: "Users" },
    { id: 2, title: "Учет рабочего времени", description: "Автоматическое формирование табелей и интеграция с 1С.", icon: "Clock" },
    { id: 3, title: "Аппаратная независимость", description: "Поддержка контроллеров различных производителей по протоколу OSDP.", icon: "Server" },
    { id: 4, title: "Защита от двойного прохода", description: "Глобальный Anti-passback на всей территории предприятия.", icon: "Shield" }
  ],
  documents: [
    { id: 1, name: "Прайс-лист на оборудование 2024", url: "#", type: "price" },
    { id: 2, name: "Руководство администратора СКУД", url: "#", type: "doc" },
    { id: 3, name: "Выписка из реестра Минцифры", url: "#", type: "registry" }
  ],
  contacts: {
    phone: "+7 (495) 123-45-67",
    email: "support@strazh-avangard.ru",
    address: "г. Москва, Инновационный проезд, д. 1"
  }
};

export default function App() {
  const [data, setData] = useState(initialData);
  const [isAdmin, setIsAdmin] = useState(false);
  const [messages, setMessages] = useState([]);
  const [toast, setToast] = useState(null);

  const showToast = (message) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  };

  const handleSupportSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const newMessage = {
      id: Date.now(),
      name: formData.get('name'),
      email: formData.get('email'),
      company: formData.get('company'),
      message: formData.get('message'),
      date: new Date().toLocaleString()
    };
    setMessages([newMessage, ...messages]);
    e.target.reset();
    showToast('Ваша заявка успешно отправлена в техподдержку!');
  };

  // --- Компонент: Публичная часть (Лендинг) ---
  const LandingView = () => (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
      {/* Навигация */}
      <nav className="fixed w-full bg-white/90 backdrop-blur-md shadow-sm z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-3">
              <div className="bg-blue-900 p-2 rounded-lg">
                <Shield className="h-8 w-8 text-white" />
              </div>
              <div>
                <span className="font-bold text-xl tracking-tight text-slate-900 block leading-none">СТРАЖЪ</span>
                <span className="text-xs font-semibold text-blue-600 tracking-widest uppercase">Авангардъ</span>
              </div>
            </div>
            <div className="hidden md:flex space-x-8">
              <a href="#features" className="text-slate-600 hover:text-blue-600 transition font-medium">Возможности</a>
              <a href="#registry" className="text-slate-600 hover:text-blue-600 transition font-medium">Реестр ПО</a>
              <a href="#documents" className="text-slate-600 hover:text-blue-600 transition font-medium">Документы</a>
              <a href="#support" className="text-slate-600 hover:text-blue-600 transition font-medium">Поддержка</a>
            </div>
            <div>
              <button
                onClick={() => setIsAdmin(true)}
                className="p-2 text-slate-400 hover:text-slate-800 transition rounded-full hover:bg-slate-100"
                title="Вход в панель администратора"
              >
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Главный экран */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        <div className="absolute inset-0 z-0">
          <img
            src={data.hero.imageUrl}
            alt="СКУД Фон"
            className="w-full h-full object-cover opacity-20"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-blue-950 via-slate-900/90 to-slate-900/80"></div>
        </div>
        <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center lg:text-left flex flex-col lg:flex-row items-center">
          <div className="lg:w-1/2">
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-white leading-tight mb-6">
              {data.hero.title}
            </h1>
            <p className="text-lg md:text-xl text-slate-300 mb-10 max-w-2xl mx-auto lg:mx-0">
              {data.hero.subtitle}
            </p>
            <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 justify-center lg:justify-start">
              <a href="#support" className="px-8 py-4 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl transition shadow-lg flex items-center justify-center">
                Запросить КП <ChevronRight className="ml-2 w-5 h-5" />
              </a>
              <a href="#documents" className="px-8 py-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition shadow-lg flex items-center justify-center border border-slate-700">
                Скачать прайс
              </a>
            </div>
          </div>
          <div className="hidden lg:block lg:w-1/2 p-12">
            {/* Иллюстрация или интерфейс */}
            <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700 rounded-2xl p-6 shadow-2xl transform rotate-2 hover:rotate-0 transition duration-500">
              <div className="flex items-center space-x-2 mb-4 border-b border-slate-700 pb-4">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <div className="text-slate-400 text-xs ml-2 font-mono">strazh-admin-panel</div>
              </div>
              <div className="space-y-4">
                <div className="h-8 bg-slate-700/50 rounded-lg w-3/4"></div>
                <div className="h-8 bg-slate-700/50 rounded-lg w-full"></div>
                <div className="h-8 bg-slate-700/50 rounded-lg w-5/6"></div>
                <div className="h-32 bg-blue-900/30 border border-blue-800/50 rounded-lg w-full mt-6 flex items-center justify-center">
                  <Shield className="w-12 h-12 text-blue-500/50" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Реестр ПО */}
      <section id="registry" className="py-16 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-blue-50 rounded-3xl p-8 md:p-12 flex flex-col md:flex-row items-center border border-blue-100">
            <div className="md:w-1/3 flex justify-center mb-8 md:mb-0">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-200 blur-xl rounded-full opacity-50"></div>
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f3/Flag_of_Russia.svg/320px-Flag_of_Russia.svg.png" alt="Флаг РФ" className="relative w-32 h-auto rounded shadow-sm opacity-90" />
              </div>
            </div>
            <div className="md:w-2/3 md:pl-12 text-center md:text-left">
              <h2 className="text-3xl font-bold text-slate-900 mb-4">{data.registry.title}</h2>
              <p className="text-lg text-slate-700 leading-relaxed">
                {data.registry.description}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Возможности */}
      <section id="features" className="py-24 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Ключевые возможности</h2>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">Инновационные решения для обеспечения безопасности объектов любой сложности.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {data.features.map(feature => {
              const IconComponent = { Users, Clock, Server, Shield }[feature.icon] || CheckCircle;
              return (
                <div key={feature.id} className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-md transition border border-slate-100">
                  <div className="w-14 h-14 bg-blue-100 rounded-xl flex items-center justify-center mb-6 text-blue-600">
                    <IconComponent className="w-7 h-7" />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-3">{feature.title}</h3>
                  <p className="text-slate-600 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Документы и файлы */}
      <section id="documents" className="py-24 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Документация и прайс-листы</h2>
            <p className="text-lg text-slate-600">Вся необходимая информация для проектирования и закупок.</p>
          </div>
          <div className="bg-slate-50 rounded-2xl border border-slate-200 p-2">
            {data.documents.map((doc, idx) => (
              <a
                key={doc.id}
                href={doc.url}
                className={`flex items-center justify-between p-4 md:p-6 hover:bg-white transition rounded-xl group ${idx !== data.documents.length - 1 ? 'border-b border-slate-200/60' : ''}`}
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-3 rounded-lg ${doc.type === 'price' ? 'bg-green-100 text-green-600' : 'bg-blue-100 text-blue-600'}`}>
                    <FileText className="w-6 h-6" />
                  </div>
                  <span className="font-semibold text-slate-800 group-hover:text-blue-600 transition">{doc.name}</span>
                </div>
                <div className="text-slate-400 group-hover:text-blue-600 transition">
                  <Download className="w-6 h-6" />
                </div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* Поддержка и обратная связь */}
      <section id="support" className="py-24 bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row gap-16">
            <div className="lg:w-1/2">
              <h2 className="text-3xl md:text-4xl font-bold mb-6">Техническая поддержка</h2>
              <p className="text-slate-300 text-lg mb-10 leading-relaxed">
                Наши специалисты готовы ответить на любые вопросы по внедрению, настройке и эксплуатации системы «Стражъ | Авангардъ».
              </p>

              <div className="space-y-6">
                <div className="flex items-center space-x-4 bg-slate-800 p-6 rounded-2xl border border-slate-700">
                  <Phone className="w-8 h-8 text-blue-400" />
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Горячая линия</p>
                    <p className="text-xl font-bold">{data.contacts.phone}</p>
                  </div>
                </div>
                <div className="flex items-center space-x-4 bg-slate-800 p-6 rounded-2xl border border-slate-700">
                  <Mail className="w-8 h-8 text-blue-400" />
                  <div>
                    <p className="text-sm text-slate-400 mb-1">Электронная почта</p>
                    <p className="text-xl font-bold">{data.contacts.email}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="lg:w-1/2">
              <div className="bg-white rounded-3xl p-8 text-slate-900 shadow-xl">
                <h3 className="text-2xl font-bold mb-6 text-slate-900">Оставить заявку</h3>
                <form onSubmit={handleSupportSubmit} className="space-y-5">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Ваше имя</label>
                    <input required name="name" type="text" className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" placeholder="Иван Иванов" />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Email</label>
                      <input required name="email" type="email" className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" placeholder="ivan@company.ru" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-2">Компания</label>
                      <input name="company" type="text" className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition" placeholder="ООО Завод" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">Сообщение / Суть проблемы</label>
                    <textarea required name="message" rows="4" className="w-full px-4 py-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition resize-none" placeholder="Опишите вашу задачу..."></textarea>
                  </div>
                  <button type="submit" className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl transition shadow-md">
                    Отправить заявку
                  </button>
                </form>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-950 py-10 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center text-slate-400 text-sm">
          <p>© 2024 СКУД «Стражъ | Авангардъ». Все права защищены.</p>
          <p className="mt-4 md:mt-0">{data.contacts.address}</p>
        </div>
      </footer>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-green-600 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center space-x-3 z-50 animate-bounce">
          <CheckCircle className="w-6 h-6" />
          <span className="font-medium">{toast}</span>
        </div>
      )}
    </div>
  );

  // --- Компонент: Панель Администратора ---
  const AdminView = () => {
    const [activeTab, setActiveTab] = useState('general');
    const [editData, setEditData] = useState(data);

    const handleSave = () => {
      setData(editData);
      showToast('Изменения успешно сохранены!');
    };

    const handleDocumentAdd = () => {
      const newDoc = { id: Date.now(), name: "Новый документ", url: "#", type: "doc" };
      setEditData({ ...editData, documents: [...editData.documents, newDoc] });
    };

    const handleDocumentRemove = (id) => {
      setEditData({ ...editData, documents: editData.documents.filter(d => d.id !== id) });
    };

    const deleteMessage = (id) => {
      setMessages(messages.filter(m => m.id !== id));
    };

    return (
      <div className="min-h-screen bg-slate-100 flex flex-col md:flex-row font-sans text-slate-800">
        {/* Sidebar */}
        <div className="w-full md:w-64 bg-slate-900 text-white flex flex-col shadow-2xl z-10">
          <div className="p-6 border-b border-slate-800 flex justify-between items-center">
            <h2 className="font-bold text-lg flex items-center">
              <Shield className="w-5 h-5 mr-2 text-blue-500" /> Админ-панель
            </h2>
            <button onClick={() => setIsAdmin(false)} className="text-slate-400 hover:text-white" title="Вернуться на сайт">
              <X className="w-5 h-5" />
            </button>
          </div>
          <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
            <button onClick={() => setActiveTab('general')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'general' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
              <LayoutDashboard className="w-5 h-5" /> <span>Главная & Тексты</span>
            </button>
            <button onClick={() => setActiveTab('registry')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'registry' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
              <CheckCircle className="w-5 h-5" /> <span>Реестр ПО</span>
            </button>
            <button onClick={() => setActiveTab('files')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'files' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
              <FileText className="w-5 h-5" /> <span>Файлы & Прайсы</span>
            </button>
            <button onClick={() => setActiveTab('messages')} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'messages' ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-slate-800'}`}>
              <MessageSquare className="w-5 h-5" />
              <span>Заявки</span>
              {messages.length > 0 && <span className="ml-auto bg-blue-500 text-xs py-0.5 px-2 rounded-full">{messages.length}</span>}
            </button>
          </nav>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col max-h-screen overflow-hidden">
          <header className="bg-white shadow-sm p-4 flex justify-between items-center">
            <h1 className="text-xl font-bold text-slate-800">
              {activeTab === 'general' && "Настройки главной страницы"}
              {activeTab === 'registry' && "Реестр и Сертификаты"}
              {activeTab === 'files' && "Управление файлами"}
              {activeTab === 'messages' && "Обратная связь"}
            </h1>
            {activeTab !== 'messages' && (
              <button onClick={handleSave} className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition font-medium">
                <Save className="w-4 h-4" /> <span>Сохранить на сайте</span>
              </button>
            )}
          </header>

          <main className="flex-1 p-6 overflow-y-auto">
            <div className="max-w-4xl mx-auto">

              {/* Tab: General */}
              {activeTab === 'general' && (
                <div className="space-y-6">
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="font-bold text-lg mb-4 border-b pb-2">Секция "Hero" (Главный экран)</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Заголовок</label>
                        <input type="text" value={editData.hero.title} onChange={e => setEditData({ ...editData, hero: { ...editData.hero, title: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Подзаголовок</label>
                        <textarea rows="3" value={editData.hero.subtitle} onChange={e => setEditData({ ...editData, hero: { ...editData.hero, subtitle: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1"><ImageIcon className="inline w-4 h-4 mr-1" /> Ссылка на фоновое изображение (URL)</label>
                        <input type="text" value={editData.hero.imageUrl} onChange={e => setEditData({ ...editData, hero: { ...editData.hero, imageUrl: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="font-bold text-lg mb-4 border-b pb-2">Контакты техподдержки</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Телефон</label>
                        <input type="text" value={editData.contacts.phone} onChange={e => setEditData({ ...editData, contacts: { ...editData.contacts, phone: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-600 mb-1">Email</label>
                        <input type="text" value={editData.contacts.email} onChange={e => setEditData({ ...editData, contacts: { ...editData.contacts, email: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                      <div className="md:col-span-2">
                        <label className="block text-sm font-medium text-slate-600 mb-1">Адрес</label>
                        <input type="text" value={editData.contacts.address} onChange={e => setEditData({ ...editData, contacts: { ...editData.contacts, address: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab: Registry */}
              {activeTab === 'registry' && (
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                  <h3 className="font-bold text-lg mb-4 border-b pb-2">Информация о реестре российского ПО</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-600 mb-1">Заголовок блока</label>
                      <input type="text" value={editData.registry.title} onChange={e => setEditData({ ...editData, registry: { ...editData.registry, title: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-600 mb-1">Текст описания (номер приказа и т.д.)</label>
                      <textarea rows="6" value={editData.registry.description} onChange={e => setEditData({ ...editData, registry: { ...editData.registry, description: e.target.value } })} className="w-full px-4 py-2 rounded border focus:ring-2 focus:ring-blue-500 outline-none" />
                    </div>
                  </div>
                </div>
              )}

              {/* Tab: Files */}
              {activeTab === 'files' && (
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                  <div className="flex justify-between items-center mb-6 border-b pb-4">
                    <h3 className="font-bold text-lg">Управление файлами для скачивания</h3>
                    <button onClick={handleDocumentAdd} className="flex items-center space-x-1 text-sm bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded transition">
                      <Plus className="w-4 h-4" /> <span>Добавить файл</span>
                    </button>
                  </div>
                  <div className="space-y-4">
                    {editData.documents.map((doc, idx) => (
                      <div key={doc.id} className="flex flex-col md:flex-row gap-4 items-start md:items-center p-4 bg-slate-50 border border-slate-200 rounded-lg">
                        <div className="flex-1 w-full">
                          <label className="block text-xs text-slate-500 mb-1">Название документа</label>
                          <input
                            type="text"
                            value={doc.name}
                            onChange={e => {
                              const newDocs = [...editData.documents];
                              newDocs[idx].name = e.target.value;
                              setEditData({ ...editData, documents: newDocs });
                            }}
                            className="w-full px-3 py-1.5 rounded border focus:border-blue-500 outline-none text-sm"
                          />
                        </div>
                        <div className="flex-1 w-full">
                          <label className="block text-xs text-slate-500 mb-1">URL (Ссылка на файл)</label>
                          <input
                            type="text"
                            value={doc.url}
                            onChange={e => {
                              const newDocs = [...editData.documents];
                              newDocs[idx].url = e.target.value;
                              setEditData({ ...editData, documents: newDocs });
                            }}
                            className="w-full px-3 py-1.5 rounded border focus:border-blue-500 outline-none text-sm"
                          />
                        </div>
                        <div className="w-full md:w-32">
                          <label className="block text-xs text-slate-500 mb-1">Тип</label>
                          <select
                            value={doc.type}
                            onChange={e => {
                              const newDocs = [...editData.documents];
                              newDocs[idx].type = e.target.value;
                              setEditData({ ...editData, documents: newDocs });
                            }}
                            className="w-full px-3 py-1.5 rounded border outline-none text-sm bg-white"
                          >
                            <option value="doc">Документ</option>
                            <option value="price">Прайс-лист</option>
                            <option value="registry">Реестр</option>
                          </select>
                        </div>
                        <div className="pt-5">
                          <button onClick={() => handleDocumentRemove(doc.id)} className="p-2 text-red-500 hover:bg-red-50 rounded" title="Удалить">
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    ))}
                    {editData.documents.length === 0 && (
                      <div className="text-center py-8 text-slate-400">Нет добавленных файлов</div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab: Messages */}
              {activeTab === 'messages' && (
                <div className="space-y-4">
                  {messages.length === 0 ? (
                    <div className="bg-white p-10 rounded-xl shadow-sm border border-slate-200 text-center text-slate-500 flex flex-col items-center">
                      <MessageSquare className="w-12 h-12 text-slate-300 mb-3" />
                      <p>Новых заявок пока нет.</p>
                    </div>
                  ) : (
                    messages.map(msg => (
                      <div key={msg.id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 relative">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-bold text-slate-800">{msg.name} <span className="text-slate-500 font-normal text-sm ml-2">({msg.email})</span></h4>
                            {msg.company && <p className="text-sm text-blue-600 font-medium">{msg.company}</p>}
                          </div>
                          <div className="flex items-center space-x-3">
                            <span className="text-xs text-slate-400">{msg.date}</span>
                            <button onClick={() => deleteMessage(msg.id)} className="text-slate-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
                          </div>
                        </div>
                        <div className="mt-3 p-3 bg-slate-50 rounded text-slate-700 text-sm whitespace-pre-wrap">
                          {msg.message}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

            </div>
          </main>
        </div>

        {/* Admin Toast Notification */}
        {toast && (
          <div className="fixed bottom-6 right-6 bg-slate-800 text-white px-6 py-4 rounded-xl shadow-2xl flex items-center space-x-3 z-50">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="font-medium text-sm">{toast}</span>
          </div>
        )}
      </div>
    );
  };

  return isAdmin ? <AdminView /> : <LandingView />;
}