APP_VERSION = "1.1.9"

def versionfile_generator():
    template = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({APP_VERSION.replace('.', ',')}, 0),
    prodvers=({APP_VERSION.replace('.', ',')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'MVA'),
        StringStruct('FileDescription', 'Relatório do Estoque'),
        StringStruct('FileVersion', '{APP_VERSION}'),
        StringStruct('InternalName', 'RelatorioEstoque'),
        StringStruct('LegalCopyright', '© 2026 MVA'),
        StringStruct('OriginalFilename', 'Relatório do Estoque.exe'),
        StringStruct('ProductName', 'Sistema de Relatórios'),
        StringStruct('ProductVersion', '{APP_VERSION}')])
      ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    with open("version.txt", "w", encoding="utf-8") as f:
        f.write(template)

if __name__ == "__main__":
    versionfile_generator()
