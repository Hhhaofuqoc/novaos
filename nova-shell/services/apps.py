"""Descoberta real via XDG .desktop; sem lançadores fictícios."""
from gi.repository import Gio

CATEGORIES = ['Favoritos','Todos os aplicativos','Desenvolvimento','Escritório',
              'Gráficos','Internet','Multimídia','Sistema','Configurações','Utilitários']
MATCH = {
    'Desenvolvimento': ('Development', 'IDE'),
    'Escritório': ('Office',),
    'Gráficos': ('Graphics', 'Photography'),
    'Internet': ('Network', 'WebBrowser'),
    'Multimídia': ('AudioVideo', 'Audio', 'Video', 'Player'),
    'Sistema': ('System',),
    'Configurações': ('Settings',),
    'Utilitários': ('Utility', 'Accessories'),
}

def installed():
    items = {}
    for app in Gio.AppInfo.get_all():
        try:
            ident = app.get_id()
            if ident and app.should_show() and app.get_name() and app.get_executable():
                items[ident] = app
        except Exception:
            continue
    return dict(sorted(items.items(), key=lambda row: row[1].get_name().casefold()))

def category(app, name):
    if name in ('Todos os aplicativos', 'Favoritos'): return True
    try: cats = (app.get_categories() or '').split(';')
    except (AttributeError, TypeError): cats = []
    return any(c in MATCH.get(name, ()) for c in cats)

def launch(app):
    return app.launch([], None)
