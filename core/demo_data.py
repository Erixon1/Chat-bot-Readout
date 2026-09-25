"""Respuestas simuladas para MODO DEMO (sin API key). Temática: Biblioteca Inteligente & Préstamo de Libros Readout."""
import random

CLEAN_CODE = """### [Ingeniería de Software] Clean Code: Manual de Estilo Ágil
**Autor:** Robert C. Martin ("Uncle Bob") · **Categoría:** Tecnología & Desarrollo · **Plazo de Préstamo:** 7 días · **Fianza Ref:** S/ 15.00

**Síntesis y Pilares Clave:**
- **Nombres con significado:** Las variables, funciones y clases deben revelar su intención sin necesidad de comentarios redundantes.
- **Funciones pequeñas y de responsabilidad única (SRP):** Una función solo debe hacer una cosa y hacerla excepcionalmente bien.
- **Regla del Boy Scout:** Deja el código base siempre más limpio de lo que lo encontraste al abrirlo.
- **Tratamiento de errores estructurado:** Preferir excepciones a códigos de error retornados; evitar pasar nulos.
- **Principios SOLID:** Fundamentos de arquitectura limpia, desacoplamiento y testabilidad mediante TDD.

*Ideal para ingenieros de software, desarrolladores y arquitectos de sistemas.*"""

CIEN_ANOS = """### [Literatura Universal] Cien Años de Soledad
**Autor:** Gabriel García Márquez (Premio Nobel 1982) · **Categoría:** Realismo Mágico · **Plazo de Préstamo:** 14 días · **Fianza Ref:** S/ 10.00

**Síntesis y Aspectos Destacados:**
- **La epopeya de Macondo:** Crónica monumental de siete generaciones de la familia Buendía, entrelazando lo mítico con la historia colombiana y latinoamericana.
- **Temas centrales:** La soledad inexorable, la repetición cíclica del tiempo, el incesto como tabú trágico y la memoria histórica.
- **Estilo y Realismo Mágico:** Prosa lírica y envolvente donde lo extraordinario se narra con naturalidad cotidiana.

*Obra cumbre de las letras hispanas y lectura del patrimonio literario universal.*"""

ARTE_GUERRA = """### [Estrategia & Filosofía] El Arte de la Guerra
**Autor:** Sun Tzu · **Categoría:** Estrategia, Liderazgo & Toma de Decisiones · **Plazo de Préstamo:** 7 días · **Fianza Ref:** S/ 8.00

**Principios Estratégicos Fundamentales:**
- **La victoria suprema:** "El supremo arte de la guerra es someter al enemigo sin luchar".
- **Conocimiento dual:** "Conoce a tu enemigo y conócete a ti mismo; en cien batallas nunca estarás en peligro".
- **Adaptabilidad:** La estrategia debe moldearse en tiempo real según las condiciones del entorno.
- **Cálculo y logística:** La victoria se determina antes de librar el combate mediante la preparación rigurosa.

*Indispensable para gestores de proyectos, directivos y líderes de equipo.*"""

BREVE_HISTORIA = """### [Divulgación Científica] Breve Historia del Tiempo: Del Big Bang a los Agujeros Negros
**Autor:** Stephen Hawking · **Categoría:** Astrofísica & Cosmología · **Plazo de Préstamo:** 14 días · **Fianza Ref:** S/ 12.00

**Síntesis y Conceptos Explicados:**
- **El origen del cosmos:** El modelo del Big Bang, la expansión del universo y la singularidad espaciotemporal.
- **Agujeros negros y radiación de Hawking:** Cómo la gravedad cuántica predice la evaporación gradual de los horizontes de sucesos.
- **La flecha del tiempo:** Termodinámica, entropía y por qué recordamos el pasado pero no el futuro.
- **La búsqueda de la Gran Unificación:** El desafío de conciliar la Relatividad General con la Mecánica Cuántica.

*Obra de divulgación científica fundamental del siglo XX.*"""

QUIJOTE = """### [Clásicos Universales] Don Quijote de la Mancha
**Autor:** Miguel de Cervantes Saavedra · **Categoría:** Novela Clásica · **Plazo de Préstamo:** 14 días · **Fianza Ref:** S/ 10.00

**Síntesis y Valor Literario:**
- **La dualidad humana:** El contraste entre el idealismo trascendente de Don Quijote y el pragmatismo terrenal de Sancho Panza.
- **Metanarrativa moderna:** Considerada la primera novela moderna por su polifonía y juegos de autoría.
- **Crítica y sátira:** Parodia de las novelas de caballería que reflexiona sobre la justicia, la libertad y la locura lúcida.

*Patrimonio de la lengua castellana y faro de la narrativa universal.*"""

IA_MODERNA = """### [Ciencia de la Computación] Inteligencia Artificial: Un Enfoque Moderno
**Autores:** Stuart Russell & Peter Norvig · **Categoría:** Inteligencia Artificial & Algoritmos · **Plazo de Préstamo:** 7 días · **Fianza Ref:** S/ 20.00

**Contenido y Módulos de Aprendizaje:**
- **Agentes racionales:** Modelado formal de sistemas autónomos en entornos complejos.
- **Búsqueda y optimización:** Algoritmos A*, poda alfa-beta y satisfacción de restricciones.
- **Aprendizaje Automático y Redes Neuronales:** Deep Learning, procesamiento de lenguaje natural (NLP) y visión por computadora.
- **Ética y seguridad en IA:** Gobernanza de modelos generativos y alineación.

*Texto de referencia académica estándar en ciencias de la computación.*"""

PRINCIPITO = """### [Literatura Humanista] El Principito
**Autor:** Antoine de Saint-Exupéry · **Categoría:** Fábula Filosófica · **Plazo de Préstamo:** 7 días · **Fianza Ref:** S/ 8.00

**Enseñanzas y Reflexiones:**
- **La esencia humana:** "Solo con el corazón se puede ver bien; lo esencial es invisible a los ojos".
- **La responsabilidad:** "Eres responsable para siempre de lo que has domesticado".
- **Crítica a la adultez vacía:** Reflexión sobre la autenticidad y la capacidad de asombro.

*Fábula filosófica universal para lectores de todas las edades.*"""

GENERIC = [
    "En **Readout**, disponemos de un acervo bibliográfico que abarca Literatura Universal, Ciencias de la Computación, Filosofía, Estrategia y Divulgación Científica. Puede consultar la disponibilidad de **Clean Code**, **Cien Años de Soledad**, **El Arte de la Guerra** o **Inteligencia Artificial: Un Enfoque Moderno**.",
    "El sistema de préstamos de Readout le permite solicitar ejemplares físicos o reservas de sala de lectura con plazos de 7 a 14 días. Indíqueme el título que requiere para registrar su solicitud.",
]

OFFTOPIC = (
    "Como recepcionista de la Biblioteca Readout, me especializo exclusivamente en el catálogo de libros, préstamos, reservas de sala y asesoría literaria. "
    "Por favor indíqueme si desea consultar alguna obra de nuestro catálogo o iniciar un préstamo."
)

BOOK_ENTRIES = {
    "clean code": CLEAN_CODE,
    "codigo limpio": CLEAN_CODE,
    "código limpio": CLEAN_CODE,
    "robert martin": CLEAN_CODE,
    "cien años": CIEN_ANOS,
    "cien anos": CIEN_ANOS,
    "garcia marquez": CIEN_ANOS,
    "garcía márquez": CIEN_ANOS,
    "macondo": CIEN_ANOS,
    "arte de la guerra": ARTE_GUERRA,
    "sun tzu": ARTE_GUERRA,
    "estrategia": ARTE_GUERRA,
    "breve historia": BREVE_HISTORIA,
    "hawking": BREVE_HISTORIA,
    "universo": BREVE_HISTORIA,
    "quijote": QUIJOTE,
    "cervantes": QUIJOTE,
    "molinos": QUIJOTE,
    "inteligencia artificial": IA_MODERNA,
    "norvig": IA_MODERNA,
    "russell": IA_MODERNA,
    "machine learning": IA_MODERNA,
    "principito": PRINCIPITO,
    "saint-exupery": PRINCIPITO,
    "saint exupery": PRINCIPITO,
}

SAMPLE_AUDIO_TRANSCRIPTS = {
    "solicitud_prestamo_audio.mp3": (
        "Solicitud de préstamo por voz para biblioteca: El lector solicita 1 ejemplar de Clean Code de Robert Martin "
        "y 1 ejemplar de Inteligencia Artificial de Russell y Norvig para préstamo a domicilio por 7 días. "
        "Fianza total de 35 soles. Por favor registrar el préstamo y enviar confirmación al correo usuario@gmail.com "
        "y notificar al WhatsApp 987509272."
    ),
    "resena_clean_code.mp3": (
        "Nota de voz para reseña bibliográfica: Clean Code enfatiza la importancia de escribir código legible para humanos. "
        "Aspectos indispensables a evaluar: nombres significativos de funciones, funciones de menos de 20 líneas, "
        "eliminación de duplicidad mediante principio DRY y aplicación rigurosa de TDD para garantizar alta cohesión y bajo acoplamiento."
    ),
    "reserva_sala_lectura.mp3": (
        "Audio de reserva de sala bibliotecaria: Deseo reservar un cubículo de estudio grupal para 4 investigadores "
        "este viernes de 4 a 7 de la tarde, junto con la consulta en sala de Cien Años de Soledad y Don Quijote de la Mancha. "
        "Confirmar al correo investigacion.letras@instituto.org."
    ),
}


def demo_reply(user_text: str) -> str:
    t = (user_text or "").lower()
    if any(w in t for w in ["hola", "buenas", "qué tal", "que tal", "buenos días", "buenas tardes"]):
        return (
            "Bienvenido(a) a la Recepción de **Readout**, Sistema de Gestión y Préstamo Bibliotecario.\n\n"
            "Puedo asistirle con el catálogo de libros, plazos de entrega y registro de préstamos. Obras disponibles:\n\n"
            "- *Clean Code (Robert C. Martin) - Fianza Ref: S/ 15.00 (7 días)*\n"
            "- *Cien Años de Soledad (Gabriel García Márquez) - Fianza Ref: S/ 10.00 (14 días)*\n"
            "- *El Arte de la Guerra (Sun Tzu) - Fianza Ref: S/ 8.00 (7 días)*\n"
            "- *Breve Historia del Tiempo (Stephen Hawking) - Fianza Ref: S/ 12.00 (14 días)*\n"
            "- *Don Quijote de la Mancha (Miguel de Cervantes) - Fianza Ref: S/ 10.00 (14 días)*\n"
            "- *Inteligencia Artificial: Un Enfoque Moderno (Russell & Norvig) - Fianza Ref: S/ 20.00 (7 días)*\n"
            "- *El Principito (Antoine de Saint-Exupéry) - Fianza Ref: S/ 8.00 (7 días)*\n\n"
            "Indíqueme qué ejemplar desea solicitar para tomar sus datos de registro."
        )
    for key, book_info in BOOK_ENTRIES.items():
        if key in t:
            return book_info
    if any(w in t for w in ["libro", "catalogo", "catálogo", "recomienda", "prestamo", "préstamo", "autor", "resumen", "literatura", "lectura"]):
        return random.choice(GENERIC) + f"\n\n{CLEAN_CODE}\n\n{CIEN_ANOS}"
    if any(w in t for w in ["gracias", "muchas gracias", "excelente"]):
        return "Con gusto le asisto. Si desea consultar otra obra o tramitar un préstamo, indíquelo aquí."
    return random.choice(GENERIC)
