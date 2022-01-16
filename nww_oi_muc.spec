# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['../nww_oi_muc.py', '../nwws_oi_muc_slibot.py', '../nwws_oi_ldm_encoder.py', '../nww_oi_muc_stanza.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=['slixmpp.features', 'slixmpp.features.feature_starttls', 'slixmpp.features.feature_bind', 'slixmpp.features.feature_session', 'slixmpp.features.feature_bind', 'slixmpp.features.feature_rosterver', 'slixmpp.features.feature_mechanisms', 'slixmpp.features.feature_preapproval', 'slixmpp.plugins.xep_0004', 'slixmpp.plugins.xep_0030', 'slixmpp.plugins.xep_0045', 'slixmpp.plugins.xep_0199'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='nww_oi_muc',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
