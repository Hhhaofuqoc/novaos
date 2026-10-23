#!/usr/bin/env python3
"""Create NovaOS original, deterministic vector art and tiny window decorations.

No external images, fonts or training assets. Copyright NovaOS contributors,
MIT license. Run from any directory. Optional PNG rendering uses Inkscape.
"""
from pathlib import Path
import math
import random

ROOT = Path(__file__).resolve().parents[1]


def wallpaper(width, height, mobile=False):
    rng = random.Random(2718 if mobile else 31415)
    # Work in a common composition; portrait moves the rings upward and increases sky.
    w, h = 1920, 1080 if not mobile else 4267
    if mobile:
        w = 1920
    horizon = h * (.63 if mobile else .67)
    planet_x, planet_y = w * .53, horizon * .51
    radius = w * (.29 if mobile else .135)
    out = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {w} {h}">
<title>NovaOS — Your universe. Your system.</title>
<desc>Original vector synthwave landscape: violet ringed planet, mountains, distant city and cyan perspective grid. Created algorithmically for NovaOS.</desc>
<defs>
 <linearGradient id="sky" x2="0" y2="1"><stop stop-color="#08040F"/><stop offset=".54" stop-color="#10071F"/><stop offset="1" stop-color="#250044"/></linearGradient>
 <radialGradient id="halo"><stop stop-color="#A020F0" stop-opacity=".30"/><stop offset=".52" stop-color="#A020F0" stop-opacity=".10"/><stop offset="1" stop-color="#A020F0" stop-opacity="0"/></radialGradient>
 <radialGradient id="planet" cx=".3" cy=".2" r=".9"><stop stop-color="#C681FF"/><stop offset=".32" stop-color="#7D26C9"/><stop offset=".67" stop-color="#350B63"/><stop offset="1" stop-color="#0B0517"/></radialGradient>
 <linearGradient id="ground" x2="0" y2="1"><stop stop-color="#210738"/><stop offset=".3" stop-color="#0B061A"/><stop offset="1" stop-color="#08040F"/></linearGradient>
 <linearGradient id="ring"><stop stop-color="#00DFFF" stop-opacity=".12"/><stop offset=".45" stop-color="#EDE6FF"/><stop offset=".65" stop-color="#A020F0"/><stop offset="1" stop-color="#00DFFF" stop-opacity=".25"/></linearGradient>
 <linearGradient id="grid" x2="0" y2="1"><stop stop-color="#007BFF" stop-opacity=".12"/><stop offset="1" stop-color="#00DFFF" stop-opacity=".65"/></linearGradient>
 <filter id="glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="6"/></filter>
 <clipPath id="planetclip"><circle cx="{planet_x}" cy="{planet_y}" r="{radius}"/></clipPath>
</defs>
<rect width="{w}" height="{h}" fill="url(#sky)"/>
<ellipse cx="{planet_x}" cy="{planet_y}" rx="{radius*2.8}" ry="{radius*2.8}" fill="url(#halo)"/>
''']
    for _ in range(190 if not mobile else 330):
        x, y = rng.uniform(0,w), rng.uniform(0,horizon*.93)
        r = rng.choice([.7,.9,1.2,1.7])
        opacity = rng.uniform(.18,.65)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#EDE6FF" opacity="{opacity:.2f}"/>')
    ring = f'<ellipse cx="{planet_x}" cy="{planet_y}" rx="{radius*1.95}" ry="{radius*.35}" transform="rotate(-22 {planet_x} {planet_y})" fill="none" stroke="url(#ring)"'
    out += [ring + ' stroke-width="17" opacity=".65" filter="url(#glow)"/>', ring + ' stroke-width="4"/>',
            f'<circle cx="{planet_x}" cy="{planet_y}" r="{radius}" fill="url(#planet)" stroke="#A020F0" stroke-width="1.5"/>']
    # Fine atmospheric bands are original geometry, not a copied planetary texture.
    for j in range(15):
        y = planet_y-radius + j*radius*.145
        out.append(f'<path d="M {planet_x-radius} {y} Q {planet_x} {y+radius*.3} {planet_x+radius} {y+radius*.05}" fill="none" stroke="#D28BFF" stroke-width="{rng.uniform(1,7):.1f}" opacity=".055" clip-path="url(#planetclip)"/>')
    out.append(f'<path d="M {planet_x-radius*1.81:.1f} {planet_y+radius*.66:.1f} Q {planet_x-radius*.1:.1f} {planet_y+radius*.85:.1f} {planet_x+radius*1.81:.1f} {planet_y-radius*.66:.1f}" fill="none" stroke="url(#ring)" stroke-width="5"/>')
    # Skyline silhouette with a restrained handful of cyan windows.
    for x in range(50,w-20,35):
        bw = rng.randint(16,32); bh = rng.randint(24,130)
        y = horizon-bh
        out.append(f'<path d="M{x} {horizon}V{y}H{x+bw}V{horizon}Z" fill="#090613" stroke="#6C2195" stroke-width=".9"/>')
        for wy in range(int(y+9),int(horizon-6),13):
            if rng.random()>.48:
                out.append(f'<path d="M{x+5} {wy}h4m5 0h4" stroke="#00DFFF" opacity=".4" stroke-width="2"/>')
    # Triangulated mountain ranges, asymmetrical composition around city corridor.
    for side in (0,1):
        xs = [0,125,240,355,490,610,735,825] if side==0 else [1120,1240,1390,1505,1630,1760,1855,1920]
        peaks = [(x,horizon-rng.uniform(55,210)*(1 if side==0 else .8)) for x in xs]
        baseline=horizon+22
        points=[(xs[0],baseline)]+peaks+[(xs[-1],baseline)]
        ps=' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
        out.append(f'<polygon points="{ps}" fill="#14091F" stroke="#A020F0" stroke-width="2"/>')
        for n,(x,y) in enumerate(peaks[:-1]):
            nx,ny=peaks[n+1]; bx=(x+nx)*.5
            out.append(f'<path d="M{x:.1f} {y:.1f}L{bx:.1f} {baseline:.1f}L{nx:.1f} {ny:.1f}M{x:.1f} {y:.1f}L{nx:.1f} {baseline:.1f}" stroke="#8833BD" stroke-width="1" fill="none" opacity=".65"/>')
    out.append(f'<rect y="{horizon+22}" width="{w}" height="{h-horizon}" fill="url(#ground)"/>')
    out.append(f'<path d="M0 {horizon+22}H{w}" stroke="#A020F0" stroke-width="3" filter="url(#glow)"/>')
    # Perspective lines all converge at the same vanishing point.
    for x in range(-2300,w+2400,240):
        out.append(f'<path d="M{w*.5} {horizon+22}L{x} {h}" stroke="url(#grid)" stroke-width="1.4"/>')
    span=h-horizon-22
    for f in [.015,.038,.07,.12,.19,.29,.43,.62,.87]:
        y=horizon+22+span*f
        out.append(f'<path d="M0 {y:.1f}H{w}" stroke="#007BFF" opacity="{.2+f*.36:.2f}" stroke-width="1.4"/>')
    out += [f'<path d="M0 {horizon+23}H{w}" stroke="#00DFFF" opacity=".55"/>', '</svg>']
    return '\n'.join(out)


def icon(name, path):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><title>{name}</title><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#A020F0"/><stop offset="1" stop-color="#007BFF"/></linearGradient></defs><rect x="3" y="3" width="58" height="58" rx="16" fill="#180D2B" stroke="#7940B6"/><g stroke="#00DFFF" fill="none" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">{path}</g></svg>'''


def write_xpm(path, width, height, pixels, colors):
    rows=[f'/* XPM */\nstatic char *nova[] = {{', f'"{width} {height} {len(colors)} 1",']
    rows += [f'"{c} c {color}",' for c,color in colors.items()]
    rows += [f'"{row}"'+(',' if i<height-1 else '') for i,row in enumerate(pixels)]
    rows += ['};','']
    path.write_text('\n'.join(rows))


def xfwm(theme, light=False):
    root=ROOT/'themes'/theme/'xfwm4'; root.mkdir(parents=True,exist_ok=True)
    bg='#F0E9FF' if light else '#160B25'; inactive='#E0D8EE' if light else '#100A19'
    fg='#352047' if light else '#EDE6FF'
    for state in ['active','inactive']:
        color=bg if state=='active' else inactive
        edge='#A020F0' if state=='active' else '#443054'
        colors={' ':'None','.':color,'+':edge,'@':fg,'#':'#00DFFF'}
        for name,width,height in [('title-1',8,34),('title-2',4,34),('title-3',4,34),('title-4',4,34),('title-5',8,34),('top-left',5,34),('top-right',5,34),('left',4,4),('right',4,4),('bottom',4,4),('bottom-left',5,5),('bottom-right',5,5)]:
            pixels=[('+'*width if y==0 and ('title' in name or 'top' in name) else '.'*width) for y in range(height)]
            write_xpm(root/f'{name}-{state}.xpm',width,height,pixels,colors)
    for name in ['close','hide','maximize','maximize-toggled','shade','shade-toggled','stick','stick-toggled','menu']:
        for state in ['active','inactive','prelight','pressed']:
            color=bg if state!='inactive' else inactive
            pix=[list('.'*30) for _ in range(30)]
            def dot(x,y):
                if 0<=x<30 and 0<=y<30: pix[y][x]='#' if state=='prelight' else '@'
            if name=='close':
                for t in range(9,21):
                    for thick in (0,1): dot(t,t+thick);dot(29-t,t+thick)
            elif name=='hide':
                for x in range(8,22): dot(x,20);dot(x,21)
            elif name.startswith('maximize'):
                for x in range(9,21): dot(x,9);dot(x,20)
                for y in range(9,21):dot(9,y);dot(20,y)
                if name.endswith('toggled'):
                    for x in range(6,18):dot(x,6)
                    for y in range(6,18):dot(6,y)
            elif name.startswith('shade'):
                for x in range(9,21):dot(x,11);dot(x,12)
            elif name.startswith('stick'):
                for x in range(10,20):dot(x,11)
                for y in range(11,23):dot(15,y)
            else:
                for y in [10,15,20]:
                    for x in range(9,21):dot(x,y)
            write_xpm(root/f'{name}-{state}.xpm',30,30,[''.join(r) for r in pix],{' ':'None','.':color,'@':fg,'#':'#00DFFF'})
    (root/'themerc').write_text(f'''# NovaOS original XFWM4 decoration
active_text_color={fg}
inactive_text_color={'#74677F' if light else '#90829F'}
active_text_shadow_color={bg}
inactive_text_shadow_color={inactive}
active_text_shadow=none
inactive_text_shadow=none
title_alignment=center
title_horizontal_offset=6
title_vertical_offset_active=0
title_vertical_offset_inactive=0
button_spacing=4
button_offset=5
maximized_offset=0
show_app_icon=true
full_width_title=true
''')


def main():
    (ROOT/'wallpapers').mkdir(exist_ok=True)
    (ROOT/'wallpapers'/'novaos-desktop.svg').write_text(wallpaper(3840,2160))
    (ROOT/'wallpapers'/'novaos-mobile.svg').write_text(wallpaper(1080,2400,True))
    icons = {
      'novaos':'<path d="M17 45V20l30 25V20M22 16h20"/><circle cx="47" cy="16" r="2" fill="#A020F0" stroke="none"/>',
      'novaos-terminal':'<rect x="13" y="16" width="38" height="32" rx="5"/><path d="m20 26 7 6-7 6m13 2h11"/>',
      'novaos-files':'<path d="M12 23v-5h16l5 6h19v23H12Zm0 1h40"/>',
      'novaos-browser':'<circle cx="32" cy="32" r="19"/><ellipse cx="32" cy="32" rx="8" ry="19"/><path d="M14 25h36M14 39h36"/>',
      'novaos-music':'<path d="M29 40V19l19-4v21M29 25l19-4"/><ellipse cx="23" cy="42" rx="6" ry="5"/><ellipse cx="42" cy="38" rx="6" ry="5"/>',
      'novaos-settings':'<path d="M17 18v28m15-28v28m15-28v28"/><rect x="12" y="23" width="10" height="7" rx="2" fill="#180D2B"/><rect x="27" y="35" width="10" height="7" rx="2" fill="#180D2B"/><rect x="42" y="22" width="10" height="7" rx="2" fill="#180D2B"/>',
      'novaos-monitor':'<rect x="12" y="15" width="40" height="30" rx="4"/><path d="M18 32h7l4-9 6 15 4-7h7M32 45v6m-9 0h18"/>',
      'novaos-notes':'<path d="M18 12h23l7 7v33H18Zm23 0v9h7M25 29h16M25 36h16M25 43h10"/>',
      'novaos-store':'<path d="M15 25h34l-3 26H18ZM24 25v-6a8 8 0 0 1 16 0v6M32 32v12m-6-6h12"/>',
      'novaos-updater':'<path d="M48 25a18 18 0 1 0 1 13M48 14v12H36M32 43V23m-7 7 7-7 7 7"/>',
      'novaos-editor':'<path d="m24 21-12 11 12 11m16-22 12 11-12 11m-5-26-6 30"/>',
    }
    iconroot=ROOT/'themes'/'icons'/'NovaOS'
    (iconroot/'scalable'/'apps').mkdir(parents=True,exist_ok=True)
    (iconroot/'index.theme').write_text('''[Icon Theme]
Name=NovaOS
Comment=Original NovaOS neon application icons
Inherits=Adwaita,hicolor
Directories=scalable/apps

[scalable/apps]
Size=64
MinSize=16
MaxSize=256
Type=Scalable
Context=Applications
''')
    for name,path in icons.items():(iconroot/'scalable'/'apps'/f'{name}.svg').write_text(icon(name,path))
    for theme,light in [('NovaOS-Dark',False),('NovaOS-Light',True)]:xfwm(theme,light)


if __name__=='__main__':main()
