#!/usr/bin/env python3
"""Constrói SVGs próprios da NovaOS; não copia fontes externas."""
from pathlib import Path
from html import escape
DEST=Path(__file__).resolve().parents[1]/'assets/icons'
DEST.mkdir(parents=True,exist_ok=True)
# Objetos vetoriais desenhados manualmente em viewBox 128x128.
SHAPES={
 'logo': '<path d="M23 99V29l21 13 39 45V28l21-7v78L83 86 44 42v65z" fill="url(#primary)"/><path d="M23 99L44 84 83 86 104 99 83 108 44 105z" fill="url(#secondary)" opacity=".85"/>',
 'menu': '<rect x="26" y="26" width="30" height="30" rx="8"/><rect x="72" y="26" width="30" height="30" rx="8"/><rect x="26" y="72" width="30" height="30" rx="8"/><rect x="72" y="72" width="30" height="30" rx="8"/>',
 'terminal': '<rect x="17" y="26" width="94" height="76" rx="12" fill="#151e39" stroke="#67a5ff" stroke-width="5"/><path d="M34 48l17 16-17 16M59 82h28" fill="none" stroke="#e5dcff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>',
 'folder': '<path d="M12 39q0-10 11-10h26l13 12h43q11 0 11 11v45q0 11-11 11H24q-12 0-12-11z" fill="url(#primary)"/><path d="M15 59h96v34q0 12-12 12H26q-11 0-11-12z" fill="url(#secondary)"/>',
 'document': '<path d="M29 11h47l23 23v78H29q-7 0-7-7V18q0-7 7-7" fill="url(#primary)"/><path d="M76 12v23h23M40 59h40M40 76h40M40 93h26" fill="none" stroke="#e1ebff" stroke-width="6" stroke-linecap="round"/>',
 'settings': '<path d="M56 12h16l5 14 13 6 14-6 11 13-9 12 3 15 10 11-7 17-15-1-13 8-3 15H51l-4-15-13-8-14 1-8-17 10-11 2-15-9-12 10-13 14 6 13-6z" fill="url(#primary)"/><circle cx="64" cy="64" r="21" fill="#11162c"/><circle cx="64" cy="64" r="11" fill="#79caff"/>',
 'system': '<rect x="18" y="22" width="92" height="69" rx="9" fill="#141d35" stroke="#7a71fe" stroke-width="6"/><path d="M43 112h43M64 92v20M26 70l16-14 14 11 15-27 11 22 18-14" fill="none" stroke="#80caff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>',
 'music': '<path d="M55 24l53-12v68h-12V34L66 40v53H54z" fill="url(#primary)"/><ellipse cx="41" cy="94" rx="21" ry="13" transform="rotate(-13 41 94)" fill="url(#secondary)"/><ellipse cx="95" cy="82" rx="21" ry="13" transform="rotate(-13 95 82)" fill="url(#secondary)"/>',
 'video': '<rect x="14" y="25" width="100" height="78" rx="15" fill="url(#primary)"/><path d="M52 43l34 22-34 22z" fill="#f2ecff"/>',
 'gallery': '<rect x="15" y="20" width="98" height="89" rx="13" fill="#16213f" stroke="#668eff" stroke-width="5"/><circle cx="84" cy="45" r="12" fill="#b983ff"/><path d="M22 92l28-34 22 21 13-12 22 25z" fill="url(#secondary)"/>',
 'network': '<path d="M16 48q48-45 96 0M29 63q35-31 70 0M43 78q21-17 42 0" fill="none" stroke="url(#primary)" stroke-width="9" stroke-linecap="round"/><circle cx="64" cy="98" r="9" fill="#86d6ff"/>',
 'battery': '<rect x="14" y="35" width="91" height="58" rx="9" fill="none" stroke="#93b8ff" stroke-width="7"/><rect x="107" y="54" width="9" height="20" rx="3"/><rect x="22" y="43" width="64" height="42" rx="4" fill="url(#secondary)"/>',
 'audio': '<path d="M17 51h23l26-23v72L40 77H17z" fill="url(#primary)"/><path d="M79 48q20 16 0 32M89 33q35 31 0 63" stroke="#80d2ff" stroke-width="7" fill="none" stroke-linecap="round"/>',
 'power': '<path d="M64 13v49M42 26a47 47 0 1 0 44 0" stroke="url(#primary)" stroke-width="12" stroke-linecap="round" fill="none"/>',
 'trash': '<path d="M30 35h68l-7 78H37z" fill="url(#primary)"/><path d="M22 31h84M48 18h32M50 53v42M77 53v42" stroke="#d9edff" stroke-width="7" stroke-linecap="round" fill="none"/>',
 'monitor': '<rect x="13" y="24" width="102" height="77" rx="13" fill="#141b34" stroke="#746bf6" stroke-width="6"/><path d="M21 78l20-19 15 10 17-25 14 27 20-16" fill="none" stroke="#6ce6ed" stroke-width="6" stroke-linejoin="round"/>',
 'code': '<path d="M45 31L18 64l27 33M83 31l27 33-27 33M75 24L54 103" stroke="url(#secondary)" stroke-width="10" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
 'update': '<path d="M24 57a42 42 0 0 1 72-20l8 8V21M104 45H80M104 71a42 42 0 0 1-72 19l-8-8v25M24 82h24" stroke="url(#primary)" stroke-width="9" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',
 'calendar': '<rect x="18" y="29" width="92" height="83" rx="10" fill="#16203c" stroke="#8385fc" stroke-width="6"/><path d="M18 52h92M44 17v24M83 17v24" fill="none" stroke="#9ed0ff" stroke-width="7" stroke-linecap="round"/><path d="M42 74h11M76 74h11M42 93h11M76 93h11" stroke="#a38cff" stroke-width="7" stroke-linecap="round"/>',
 'user': '<circle cx="64" cy="44" r="24" fill="url(#primary)"/><path d="M20 113q0-37 44-37t44 37z" fill="url(#secondary)"/>',
}

TEMPLATE='''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128" role="img" aria-label="NovaOS {name}">
 <defs><linearGradient id="primary" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#af55fb"/><stop offset="1" stop-color="#4b5ff9"/></linearGradient>
 <linearGradient id="secondary" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#6978ff"/><stop offset="1" stop-color="#5bd5eb"/></linearGradient></defs>
 {paths}
</svg>
'''
for name,svg in SHAPES.items():
    (DEST/f'{name}.svg').write_text(TEMPLATE.format(name=escape(name), paths=svg),encoding='utf-8')
(DEST.parents[0]/'logos').mkdir(parents=True,exist_ok=True)
(DEST.parents[0]/'logos'/'NovaOS.svg').write_text((DEST/'logo.svg').read_text(),encoding='utf-8')
print('SVGs originais:',len(SHAPES))
