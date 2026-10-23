from sqlalchemy.orm import Session
from app.models import CompromisoRecurso, Ong, Item, ong_items
from app.config import Configuracion


# 5 ONGs
ONGS_SEED = [
    {
        "cuit": "30-12345678-9",
        "razon_social": "Fundación Cruz Roja Argentina",
        "email": "contacto@cruzroja.org.ar"
    },
    {
        "cuit": "30-23456789-0",
        "razon_social": "Bomberos Voluntarios Unidos",
        "email": "info@bomberosunidos.org"
    },
    {
        "cuit": "30-34567890-1",
        "razon_social": "Médicos Sin Fronteras Argentina",
        "email": "argentina@msf.org"
    },
    {
        "cuit": "30-45678901-2",
        "razon_social": "Defensa Civil Nacional",
        "email": "operaciones@defensacivil.gob.ar"
    },
    {
        "cuit": "30-56789012-3",
        "razon_social": "Fundación Emergencias Solidarias",
        "email": "ayuda@emergenciassolidarias.org"
    }
]

# 100 items temática emergencia
ITEMS_SEED = [
    # Equipamiento médico básico (1-20)
    {"nombre": "Camilla plegable", "descripcion": "Camilla de aluminio plegable para transporte de pacientes"},
    {"nombre": "Camilla rígida", "descripcion": "Camilla rígida con inmovilizadores laterales"},
    {"nombre": "Camilla cuchara", "descripcion": "Camilla tipo cuchara para rescate en espacios confinados"},
    {"nombre": "Collar cervical ajustable", "descripcion": "Collar cervical talla única ajustable para inmovilización"},
    {"nombre": "Tabla espinal", "descripcion": "Tabla espinal con correas de sujeción y orificios para manejo"},
    {"nombre": "Férula neumática pierna", "descripcion": "Férula neumática para inmovilización de fracturas de miembro inferior"},
    {"nombre": "Férula neumática brazo", "descripcion": "Férula neumática para inmovilización de fracturas de miembro superior"},
    {"nombre": "Férula de tracción", "descripcion": "Férula de tracción para fracturas de fémur"},
    {"nombre": "Mochila de primeros auxilios", "descripcion": "Mochila completa con suministros para atención primaria"},
    {"nombre": "Botiquín táctico", "descripcion": "Botiquín compacto tipo IFAK para respuesta inmediata"},
    {"nombre": "Desfibrilador externo automático (DEA)", "descripcion": "DEA semiautomático con electrodos adulto/pediátrico"},
    {"nombre": "Monitor de signos vitales", "descripcion": "Monitor portátil ECG, SpO2, NIBP, temperatura"},
    {"nombre": "Ventilador manual (Ambu)", "descripcion": "Resucitador manual adulto con mascarillas y reservorio"},
    {"nombre": "Ventilador manual pediátrico", "descripcion": "Resucitador manual pediátrico/neonatal"},
    {"nombre": "Aspirador de secreciones portátil", "descripcion": "Aspirador a batería para manejo de vía aérea"},
    {"nombre": "Laringoscopio set completo", "descripcion": "Set laringoscopio con hojas Miller y Macintosh"},
    {"nombre": "Tubos endotraqueales set", "descripcion": "Set tubos endotraqueales cuffed 2.0-8.0mm"},
    {"nombre": "Mascarillas laríngeas", "descripcion": "Mascarillas laríngeas tallas 1-5"},
    {"nombre": "Cánulas nasales oxígeno", "descripcion": "Cánulas nasales adulto y pediátrico con tubo 2m"},
    {"nombre": "Mascarillas Venturi", "descripcion": "Kit mascarillas Venturi 24-60% FiO2"},

    # Medicamentos e insumos (21-40)
    {"nombre": "Adrenalina 1mg/1ml", "descripcion": "Adrenalina 1:1000 ampollas para anafilaxia/paro cardíaco"},
    {"nombre": "Amiodarona 150mg/3ml", "descripcion": "Amiodarona IV para arritmias ventriculares"},
    {"nombre": "Atropina 1mg/10ml", "descripcion": "Atropina sulfato para bradicardia sintomática"},
    {"nombre": "Dextrosa 50% 50ml", "descripcion": "Glucosa hipertónica para hipoglucemia severa"},
    {"nombre": "Suero fisiológico 500ml", "descripcion": "Cloruro de sodio 0.9% bolsas 500ml"},
    {"nombre": "Ringer lactato 1000ml", "descripcion": "Solución Ringer lactato 1000ml para reanimación"},
    {"nombre": "Hidrocortisona 100mg", "descripcion": "Hidrocortisona sódica succinato para shock/adrenal"},
    {"nombre": "Furosemida 20mg/2ml", "descripcion": "Furosemida IV para edema agudo de pulmón"},
    {"nombre": "Nitroglicerina sublingual", "descripcion": "Nitroglicerina 0.4mg comprimidos sublinguales"},
    {"nombre": "Morfina 10mg/1ml", "descripcion": "Sulfato de morfina para dolor severo/edema pulmonar"},
    {"nombre": "Midazolam 5mg/1ml", "descripcion": "Midazolam para sedación/convulsiones"},
    {"nombre": "Diazepam 10mg/2ml", "descripcion": "Diazepam para estado epiléptico"},
    {"nombre": "Ondansetrón 4mg/2ml", "descripcion": "Ondansetrón antiemético IV/IM"},
    {"nombre": "Ketorolaco 30mg/1ml", "descripcion": "Ketorolaco trometamina analgesia IV/IM"},
    {"nombre": "Dipirona 500mg/2ml", "descripcion": "Metamizol sódico analgesia/antipirético IV"},
    {"nombre": "Cefotaxima 1g", "descripcion": "Cefotaxima sódica antibiótico 3ra generación"},
    {"nombre": "Ceftriaxona 1g", "descripcion": "Ceftriaxona sódica antibiótico 3ra generación"},
    {"nombre": "Ampicilina/Sulbactam 1.5g", "descripcion": "Ampicilina/sulbactam para infecciones mixtas"},
    {"nombre": "Metronidazol 500mg/100ml", "descripcion": "Metronidazol IV para anaerobios"},
    {"nombre": "Cloranfenicol 1g", "descripcion": "Cloranfenicol succinato para meningitis/septimia"},

    # Material de curación y vendaje (41-60)
    {"nombre": "Gasas estériles 10x10cm", "descripcion": "Gasas estériles 12 capas caja 100 unidades"},
    {"nombre": "Gasas estériles 20x20cm", "descripcion": "Gasas estériles 12 capas para quemaduras"},
    {"nombre": "Vendas elásticas 10cm", "descripcion": "Vendas elásticas adhesivas 10cm x 4.5m"},
    {"nombre": "Vendas elásticas 15cm", "descripcion": "Vendas elásticas adhesivas 15cm x 4.5m"},
    {"nombre": "Venda triangular", "descripcion": "Venda triangular no tejida para cabestrillo/inmovilización"},
    {"nombre": "Esparadrapo hipoalergénico 2.5cm", "descripcion": "Esparadrapo papel hipoalergénico 2.5cm x 9m"},
    {"nombre": "Esparadrapo tela 2.5cm", "descripcion": "Esparadrapo tela resistente 2.5cm x 9m"},
    {"nombre": "Cinta adhesiva 5cm", "descripcion": "Cinta adhesiva impermeable 5cm para apósitos"},
    {"nombre": "Apósitos hidrocoloides", "descripcion": "Apósitos hidrocoloides para heridas crónicas/quemaduras"},
    {"nombre": "Apósitos de plata", "descripcion": "Apósitos antimicrobianos con plata iónica"},
    {"nombre": "Algodón hidrófilo 500g", "descripcion": "Algodón hidrófilo estéril rollo 500g"},
    {"nombre": "Apósito compresivo", "descripcion": "Apósito compresivo estéril para hemorragias"},
    {"nombre": "Torniquete táctico (CAT)", "descripcion": "Torniquete neumático combate aplicación una mano"},
    {"nombre": "Gasas hemostáticas", "descripcion": "Gasas impregnadas con caolín/quitosano para sangrado"},
    {"nombre": "Vendas hemostáticas", "descripcion": "Vendas compresivas con agente hemostático"},
    {"nombre": "Tijeras de trauma", "descripcion": "Tijeras rompuntas para corte ropa/vendas"},
    {"nombre": "Pinzas Kelly", "descripcion": "Pinzas hemostáticas rectas 14cm"},
    {"nombre": "Pinzas Mosquito", "descripcion": "Pinzas hemostáticas curvas 12cm"},
    {"nombre": "Portaagujas Mayo-Hegar", "descripcion": "Portaagujas 18cm para sutura"},
    {"nombre": "Set sutura nylon 3/0", "descripcion": "Nylon monofilamento 3/0 aguja 3/8 círculo 26mm"},

    # Equipamiento de inmovilización y rescate (61-80)
    {"nombre": "KED (Kendrick Extrication Device)", "descripcion": "Dispositivo de extricación para rescate vehicular"},
    {"nombre": "Collar cervical pediátrico", "descripcion": "Collar cervical talla pediátrica ajustable"},
    {"nombre": "Inmovilizador de cabeza", "descripcion": "Bloques de espuma con correas para inmovilización cefálica"},
    {"nombre": "Chaleco de extricación", "descripcion": "Chaleco tipo KED para extricación rápida"},
    {"nombre": "Camilla de cesto", "descripcion": "Camilla tipo cesto para rescate vertical/angosto"},
    {"nombre": "Camilla de vacío", "descripcion": "Camilla moldeable por vacío para politraumatismos"},
    {"nombre": "Sistema de elevación", "descripcion": "Polipasto y cuerdas para rescate en altura"},
    {"nombre": "Arnés de rescate", "descripcion": "Arnés integral certificado NFPA 1983"},
    {"nombre": "Casco de rescate", "descripcion": "Casco con barbiquejo y visera para rescate técnico"},
    {"nombre": "Guantes de rescate", "descripcion": "Guantes cuero kevlar corte/abrasión resistencia"},
    {"nombre": "Botas de rescate", "descripcion": "Botas puntas de acero, dieléctricas, antideslizantes"},
    {"nombre": "Linterna frontal", "descripcion": "Linterna LED frontal recargable 1000 lúmenes"},
    {"nombre": "Radio portátil", "descripcion": "Radio VHF/UHF banda ciudadana/emergencia"},
    {"nombre": "GPS portátil", "descripcion": "GPS rugged resistente agua/golpes"},
    {"nombre": "Bolsa de rescate acuático", "descripcion": "Bolsa lanza-cuerdas 20m para rescate en agua"},
    {"nombre": "Chaleco salvavidas", "descripcion": "Chaleco salvavidas tipo V rescate rápido"},
    {"nombre": "Traje seco rescate", "descripcion": "Traje seco neopreno para rescate en agua fría"},
    {"nombre": "Cuerda estática 11mm", "descripcion": "Cuerda estática 11mm 200m certificado EN 1891"},
    {"nombre": "Mosquetones seguridad", "descripcion": "Mosquetones acero triple seguro 25kN"},
    {"nombre": "Descensor figura 8", "descripcion": "Descensor figura 8 para rappel/rescate"},

    # Vehículos y equipamiento mayor (81-90)
    {"nombre": "Ambulancia tipo B", "descripcion": "Ambulancia soporte vital básico equipada"},
    {"nombre": "Ambulancia tipo C", "descripcion": "Ambulancia soporte vital avanzado UTI móvil"},
    {"nombre": "Ambulancia 4x4", "descripcion": "Ambulancia tracción integral zona rural/montaña"},
    {"nombre": "Motoambulancia", "descripcion": "Motocicleta equipada respuesta rápida urbana"},
    {"nombre": "Bicicleta de emergencia", "descripcion": "Bicicleta montaña equipada DEA y botiquín"},
    {"nombre": "Vehículo comando", "descripcion": "Vehículo puesto de mando comunicaciones satélite"},
    {"nombre": "Generador portátil 5kW", "descripcion": "Generador inverter silencioso 5kW 220V/12V"},
    {"nombre": "Torre de iluminación", "descripcion": "Torre iluminación LED 4x1000W telescópica"},
    {"nombre": "Carpa neumática médica", "descripcion": "Carpa inflable 20m2 para triage/hospital de campaña"},
    {"nombre": "Sistema purificación agua", "descripcion": "Potabilizador agua 2000L/h ósmosis inversa"},

    # Equipamiento comunicaciones y logística (91-100)
    {"nombre": "Radio base VHF", "descripcion": "Radio base VHF 50W antena omnidireccional"},
    {"nombre": "Repetidora portátil", "descripcion": "Repetidora VHF/UHF portátil batería 48h"},
    {"nombre": "Teléfono satelital", "descripcion": "Teléfono satelital Iridium/Inmarsat datos/voz"},
    {"nombre": "Terminal VSAT", "descripcion": "Terminal VSAT banda ancha satelital 10Mbps"},
    {"nombre": "Tablet rugged", "descripcion": "Tablet militar IP68 Android/Windows 10 pulgadas"},
    {"nombre": "Impresora térmica portátil", "descripcion": "Impresora térmica Bluetooth para triage/partes"},
    {"nombre": "Etiquetadora triage", "descripcion": "Etiquetadora triage START rojo/amarillo/verde/negro"},
    {"nombre": "Bolsas para cadáveres", "descripcion": "Bolsas cadáveres adulto/infantil impermeables con cremallera"},
    {"nombre": "Cámara térmica", "descripcion": "Cámara termográfica para búsqueda víctimas"},
    {"nombre": "Drone búsqueda", "descripcion": "Drone RTK cámara térmica/zoom 30min autonomía"}
]


# Tipos de recurso con unidad, con inventario fijo para probar disponibilidad y validación de ofertas
TIPOS_RECURSO_SEED = [
    {"nombre": "Paramédicos", "descripcion": "Personal paramédico certificado para atención prehospitalaria", "unidad": "personas"},
    {"nombre": "Bomberos", "descripcion": "Personal de bomberos para rescate y control de incendios", "unidad": "personas"},
    {"nombre": "Raciones de alimento", "descripcion": "Raciones individuales de alimento listas para consumir", "unidad": "raciones"},
    {"nombre": "Agua potable", "descripcion": "Agua potable envasada para distribución", "unidad": "litros"},
    {"nombre": "Camiones", "descripcion": "Camiones de carga para logística de ayuda", "unidad": "unidades"},
    {"nombre": "Frazadas", "descripcion": "Frazadas térmicas para evacuados", "unidad": "unidades"},
]

# ONG dada de baja: su inventario no cuenta en disponibilidad ni en validación
ONG_INACTIVA_SEED = {
    "cuit": "30-67890123-4",
    "razon_social": "Asociación Rescate Sur (inactiva)",
    "email": "contacto@rescatesur.org",
    "activa": False,
}

# (índice de ONG en ONGS_SEED o "inactiva", nombre del tipo, cantidad)
INVENTARIO_TIPOS_SEED = [
    (0, "Paramédicos", 40), (0, "Raciones de alimento", 2000), (0, "Frazadas", 500),
    (1, "Bomberos", 60), (1, "Camiones", 8), (1, "Paramédicos", 10),
    (2, "Paramédicos", 50), (2, "Agua potable", 5000),
    (3, "Camiones", 15), (3, "Raciones de alimento", 3000), (3, "Agua potable", 10000),
    (4, "Paramédicos", 20), (4, "Frazadas", 800), (4, "Raciones de alimento", 1000),
    ("inactiva", "Paramédicos", 30), ("inactiva", "Camiones", 5),
]

# (índice de ONG, nombre del tipo, emergencia_id, lote_id, cantidad, estado)
COMPROMISOS_SEED = [
    (0, "Paramédicos", 1, 1, 15, "COMPROMETIDO"),
    (2, "Paramédicos", 1, 1, 25, "BLOQUEADO"),
    (3, "Camiones", 1, 2, 5, "COMPROMETIDO"),
    (0, "Raciones de alimento", 2, 3, 500, "LIBERADO"),
]


def poblar_base_datos(db: Session) -> dict:
    """
    Pobla la base de datos con datos semilla si está vacía.
    Returns: dict con conteo de registros creados.
    """
    resultado = {
        "ongs_creadas": 0,
        "items_creados": 0,
        "inventario_asignado": 0,
        "tipos_recurso_creados": 0,
        "compromisos_creados": 0,
    }

    # Verificar si ya hay datos
    if db.query(Ong).first() or db.query(Item).first():
        return {"mensaje": "Base de datos ya tiene datos, saltando seed"}

    # Crear ONGs
    ongs_creadas = []
    for ong_data in ONGS_SEED:
        # Verificar si ya existe por CUIT
        existente = db.query(Ong).filter(Ong.cuit == ong_data["cuit"]).first()
        if not existente:
            ong = Ong(**ong_data)
            db.add(ong)
            ongs_creadas.append(ong)

    db.flush()  # Para obtener IDs

    resultado["ongs_creadas"] = len(ongs_creadas)

    # Crear Items
    items_creados = []
    for item_data in ITEMS_SEED:
        # Verificar si ya existe por nombre
        existente = db.query(Item).filter(Item.nombre == item_data["nombre"]).first()
        if not existente:
            item = Item(**item_data)
            db.add(item)
            items_creados.append(item)

    db.flush()

    resultado["items_creados"] = len(items_creados)

    # Asignar inventario aleatorio a cada ONG
    import random
    random.seed(42)  # Para reproducibilidad

    for ong in ongs_creadas:
        # Cada ONG tiene entre 15-30 items diferentes
        num_items = random.randint(15, 30)
        items_seleccionados = random.sample(items_creados, min(num_items, len(items_creados)))

        for item in items_seleccionados:
            cantidad = random.randint(1, 50)
            # Insertar en tabla de asociación
            db.execute(
                ong_items.insert().values(
                    ong_id=ong.id,
                    item_id=item.id,
                    cantidad=cantidad
                )
            )
            resultado["inventario_asignado"] += 1

    poblar_tipos_recurso(db, ongs_creadas, resultado)
    db.commit()
    return resultado


def poblar_tipos_recurso(db: Session, ongs_creadas: list[Ong], resultado: dict) -> None:
    ong_inactiva = Ong(**ONG_INACTIVA_SEED)
    db.add(ong_inactiva)
    tipos = {datos["nombre"]: Item(**datos) for datos in TIPOS_RECURSO_SEED}
    db.add_all(tipos.values())
    db.flush()
    resultado["ongs_creadas"] += 1
    resultado["tipos_recurso_creados"] = len(tipos)

    def ong_de(indice) -> Ong:
        return ong_inactiva if indice == "inactiva" else ongs_creadas[indice]

    for indice, nombre, cantidad in INVENTARIO_TIPOS_SEED:
        db.execute(ong_items.insert().values(ong_id=ong_de(indice).id, item_id=tipos[nombre].id, cantidad=cantidad))
        resultado["inventario_asignado"] += 1

    for indice, nombre, emergencia_id, lote_id, cantidad, estado in COMPROMISOS_SEED:
        db.add(CompromisoRecurso(
            ong_id=ong_de(indice).id, item_id=tipos[nombre].id, emergencia_id=emergencia_id,
            lote_id=lote_id, cantidad=cantidad, estado=estado,
        ))
        resultado["compromisos_creados"] += 1


def ejecutar_seed(config: Configuracion) -> dict:
    """
    Función principal para ejecutar el seed desde línea de comandos o startup.
    """
    from app.database import iniciar_base_datos

    motor, sesion_factory = iniciar_base_datos(config.database_url)
    db = sesion_factory()

    try:
        resultado = poblar_base_datos(db)
        return resultado
    finally:
        db.close()
        motor.dispose()


if __name__ == "__main__":
    # Permitir ejecutar directamente: python -m app.seed
    config = Configuracion(
        database_url="postgresql+psycopg://cloud:postgres@localhost:5432/cloud",
        jwt_secret="dev-secret",
        jwt_issuer="rescuesync-cloud",
        jwt_audience="rescuesync-cloud",
        jwt_backend_audience="rescuesync-backend"
    )
    resultado = ejecutar_seed(config)
    print(f"Seed completado: {resultado}")