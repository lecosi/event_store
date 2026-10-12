import type { EventStatus, Role } from '../types'

const characters = (n: number) => `${n} ${n === 1 ? 'carácter' : 'caracteres'}`

/**
 * Central catalog of user-visible Spanish (es-CO) texts.
 * Static texts are strings; messages with parameters are functions.
 * Add new texts under the matching area and import `es` where needed.
 */
export const es = {
  brand: 'Mis Eventos',

  common: {
    loading: 'Cargando...',
    genericError: 'Algo salió mal. Inténtalo de nuevo.',
    networkError: 'No se pudo conectar con el servidor. Revisa tu conexión e inténtalo de nuevo.',
    cancel: 'Cancelar',
    edit: 'Editar',
    delete: 'Eliminar',
    dismiss: 'Cerrar',
    previous: 'Anterior',
    next: 'Siguiente',
    paginationLabel: 'Paginación',
    page: (page: number, pages: number) => `Página ${page} de ${pages}`,
  },

  notFoundPage: {
    title: 'Página no encontrada',
    message: 'La página que buscas no existe o fue movida.',
    home: 'Volver al inicio',
  },

  nav: {
    newEvent: 'Nuevo evento',
    newSpeaker: 'Nuevo ponente',
    myEvents: 'Mis eventos',
    admin: 'Administración',
    reports: 'Reportes',
    logout: 'Cerrar sesión',
    login: 'Iniciar sesión',
    register: 'Registrarse',
  },

  auth: {
    login: {
      title: 'Iniciar sesión',
      submit: 'Iniciar sesión',
      noAccount: '¿Aún no tienes cuenta?',
      registerLink: 'Regístrate',
      failed: 'No se pudo iniciar sesión',
    },
    register: {
      title: 'Crear cuenta',
      submit: 'Crear cuenta',
      confirmPassword: 'Confirmar contraseña',
      alreadyRegistered: '¿Ya tienes una cuenta?',
      loginLink: 'Inicia sesión',
      failed: 'No se pudo crear la cuenta',
    },
  },

  events: {
    heading: 'Eventos',
    empty: 'Aún no hay eventos.',
    noMatch: (q: string) => `Ningún evento coincide con "${q}".`,
    searchLabel: 'Buscar eventos',
    searchPlaceholder: 'Buscar eventos por nombre',
    spots: (n: number) => `${n} ${n === 1 ? 'cupo' : 'cupos'}`,
    loadListFailed: 'No se pudieron cargar los eventos',
    loadFailed: 'No se pudo cargar el evento',
    notFound: 'Evento no encontrado.',
    invalidId: 'Identificador de evento no válido',
    noDescription: 'Sin descripción.',
    when: 'Cuándo:',
    where: 'Dónde:',
    spotsLabel: 'Cupos:',
    spotsAvailable: (available: number, capacity: number) =>
      `${available} de ${capacity} disponibles`,
    infoLabel: 'Información del evento',
    manageLabel: 'Administrar evento',
    register: 'Inscribirme',
    cancelRegistration: 'Cancelar inscripción',
    registrationClosed: 'Las inscripciones están cerradas.',
    cancelRegistrationClosed: 'No se puede cancelar la inscripción de un evento finalizado.',
    full: 'Este evento está lleno.',
    registrationCancelled: 'Inscripción cancelada',
    registered: 'Te has inscrito',
    edit: 'Editar evento',
    changeStatus: 'Cambiar estado',
    selectStatus: 'Selecciona un estado',
    applyStatus: 'Aplicar estado',
    statusChanged: (status: string) => `Estado cambiado a ${status}`,
    delete: 'Eliminar evento',
    downloadParticipants: 'Descargar participantes',
    deleted: 'Evento eliminado',
    confirmDelete: '¿Eliminar este evento? Esta acción no se puede deshacer.',
    form: {
      newTitle: 'Nuevo evento',
      editTitle: 'Editar evento',
      create: 'Crear evento',
      save: 'Guardar cambios',
      back: 'Volver al evento',
      created: 'Evento creado',
      updated: 'Evento actualizado',
      saveFailed: 'No se pudo guardar el evento',
      notAllowed:
        'No tienes permiso para crear o editar eventos. Solo los organizadores y administradores pueden.',
      notAllowedEdit: 'No tienes permiso para editar este evento.',
      notEditable: 'Este evento ya no se puede editar porque está cancelado o finalizado.',
    },
  },

  sessions: {
    heading: 'Sesiones',
    empty: 'Aún no hay sesiones programadas.',
    spotsAvailable: (available: number, capacity: number) =>
      `Cupos disponibles: ${available} de ${capacity}`,
    enrolled: 'Estás inscrito',
    enroll: 'Inscribirme',
    cancelEnrollment: 'Cancelar inscripción',
    enrollAria: (title: string) => `Inscribirme en la sesión ${title}`,
    cancelEnrollmentAria: (title: string) => `Cancelar inscripción en la sesión ${title}`,
    enrolledOk: 'Inscripción a la sesión realizada',
    enrollmentCancelled: 'Inscripción a la sesión cancelada',
    registerToEventFirst: 'Inscríbete al evento para poder inscribirte en sus sesiones.',
    eventNotPublished: 'El evento no está publicado: las inscripciones a sesiones están cerradas.',
    full: 'Esta sesión está llena.',
    cancelClosed: 'El evento finalizó: ya no se puede cancelar la inscripción.',
    add: 'Agregar sesión',
    save: 'Guardar sesión',
    formLabel: 'Formulario de sesión',
    title: 'Título de la sesión',
    starts: 'Inicio de la sesión',
    ends: 'Fin de la sesión',
    capacity: 'Capacidad de la sesión',
    editAria: (title: string) => `Editar sesión ${title}`,
    deleteAria: (title: string) => `Eliminar sesión ${title}`,
    confirmDelete: (title: string) => `¿Eliminar la sesión "${title}"?`,
    added: 'Sesión agregada',
    updated: 'Sesión actualizada',
    deleted: 'Sesión eliminada',
    saveFailed: 'No se pudo guardar la sesión',
    newSpeaker: 'Crear un ponente nuevo',
    notEditable: 'Este evento está cancelado o finalizado: ya no se pueden cambiar sus sesiones.',
  },

  speakers: {
    label: 'Ponente',
    searchPlaceholder: 'Buscar ponentes por nombre',
    selected: 'Ponente seleccionado:',
    searching: 'Buscando...',
    loadFailed: 'No se pudieron cargar los ponentes',
    none: 'No se encontraron ponentes',
    resultsLabel: 'Resultados de ponentes',
    newTitle: 'Nuevo ponente',
    create: 'Crear ponente',
    created: (name: string) => `Ponente "${name}" creado`,
    createFailed: 'No se pudo crear el ponente',
    notAllowed:
      'No tienes permiso para crear ponentes. Solo los organizadores y administradores pueden.',
  },

  profile: {
    title: 'Mis eventos',
    summary: (email: string, role: string) => `${email} · rol: ${role}`,
    empty: 'Aún no estás inscrito en ningún evento.',
    browse: 'Ver eventos',
    cancelRegistration: 'Cancelar inscripción',
    cancelAria: (name: string) => `Cancelar inscripción en ${name}`,
    cancelled: (name: string) => `Inscripción en "${name}" cancelada`,
    cancelFailed: 'No se pudo cancelar la inscripción',
    loadFailed: 'No se pudieron cargar tus eventos',
  },

  admin: {
    title: 'Administración de usuarios',
    notAllowed: 'No tienes permiso para administrar usuarios. Solo los administradores pueden.',
    loadFailed: 'No se pudieron cargar los usuarios',
    empty: 'Aún no hay usuarios.',
    active: 'Activo',
    inactive: 'Inactivo',
    editAria: (name: string) => `Editar usuario ${name}`,
    fullName: 'Nombre completo',
    email: 'Correo electrónico',
    role: 'Rol',
    isActive: 'Cuenta activa',
    save: 'Guardar cambios',
    noChanges: 'No hay cambios para guardar.',
    ownAccountHint: 'No puedes cambiar tu propio rol ni desactivar tu cuenta.',
    updated: 'Usuario actualizado',
    saveFailed: 'No se pudo actualizar el usuario',
  },

  reports: {
    title: 'Reporte de participantes',
    view: 'Vista',
    byEvent: 'Por evento',
    bySession: 'Por sesión',
    sessionId: 'ID de sesión',
    sessionFilter: (id: number) => `Solo participantes de la sesión ${id}`,
    clearSessionFilter: 'Quitar filtro de sesión',
    session: 'Sesión',
    sessionStart: 'Inicio',
    notAllowed:
      'No tienes permiso para ver los reportes. Solo los organizadores y administradores pueden.',
    loadFailed: 'No se pudo cargar el reporte',
    empty: 'No hay participantes con estos filtros.',
    allStatuses: 'Todos los estados',
    status: 'Estado',
    dateFrom: 'Evento desde',
    dateTo: 'Evento hasta',
    invalidRange: 'La fecha final no puede ser anterior a la fecha inicial.',
    eventFilter: (id: number) => `Solo participantes del evento ${id}`,
    clearEventFilter: 'Quitar filtro de evento',
    tableLabel: 'Participantes',
    fullName: 'Nombre completo',
    email: 'Correo electrónico',
    event: 'Evento',
    download: 'Descargar CSV',
    downloaded: 'Reporte descargado',
    downloadFailed: 'No se pudo descargar el reporte',
  },

  /** Messages of the client-side form validators (utils/*Validation.ts). */
  validators: {
    invalidEmail: 'Ingresa un correo electrónico válido',
    passwordMin: (n: number) => `La contraseña debe tener al menos ${n} caracteres`,
    passwordMismatch: 'Las contraseñas no coinciden',
    fullNameRequired: 'El nombre completo es obligatorio',
    fullNameMax: (n: number) => `El nombre completo debe tener como máximo ${n} caracteres`,
    nameRequired: 'El nombre es obligatorio',
    nameMax: (n: number) => `El nombre debe tener como máximo ${n} caracteres`,
    locationRequired: 'El lugar es obligatorio',
    locationMax: (n: number) => `El lugar debe tener como máximo ${n} caracteres`,
    descriptionMax: (n: number) => `La descripción debe tener como máximo ${n} caracteres`,
    startRequired: 'La fecha de inicio es obligatoria',
    startFuture: 'El inicio debe estar en el futuro',
    endRequired: 'La fecha de fin es obligatoria',
    endAfterStart: 'El fin debe ser posterior al inicio',
    capacityInvalid: 'La capacidad debe ser un número entero de al menos 1',
    titleRequired: 'El título es obligatorio',
    titleMax: (n: number) => `El título debe tener como máximo ${n} caracteres`,
    chooseSpeaker: 'Elige un ponente',
    sessionStartRequired: 'El inicio es obligatorio',
    sessionEndRequired: 'El fin es obligatorio',
    sessionWithinEvent: 'La sesión debe realizarse dentro de las fechas del evento',
    capacityExceedsEvent: (n: number) => `La capacidad no puede superar la del evento (${n})`,
    bioMax: (n: number) => `La biografía debe tener como máximo ${n} caracteres`,
    emailMax: (n: number) => `El correo electrónico debe tener como máximo ${n} caracteres`,
  },

  /** Field names shown in translated 422 errors, keyed by API field name. */
  fields: {
    email: 'Correo electrónico',
    password: 'Contraseña',
    full_name: 'Nombre completo',
    name: 'Nombre',
    bio: 'Biografía',
    capacity: 'Capacidad',
    start_at: 'Inicio',
    end_at: 'Fin',
    location: 'Lugar',
    description: 'Descripción',
    title: 'Título',
    speaker_id: 'Ponente',
    date_from: 'Fecha desde',
    date_to: 'Fecha hasta',
    q: 'Búsqueda',
    page: 'Página',
    size: 'Tamaño',
  } as Record<string, string>,

  /**
   * Spanish text for backend errors (see api/client.ts). The backend answers in English, so
   * `known` is keyed by its exact `detail` string. Messages that embed values are builders,
   * and Pydantic 422 items are translated by their `type` into full sentences.
   */
  errors: {
    known: {
      'Could not validate credentials':
        'No se pudieron validar las credenciales. Inicia sesión de nuevo.',
      'Invalid email or password': 'Correo electrónico o contraseña incorrectos.',
      'Insufficient permissions': 'No tienes permisos para realizar esta acción.',
      'Event not found': 'Evento no encontrado.',
      'Session not found': 'Sesión no encontrada.',
      'Speaker not found': 'Ponente no encontrado.',
      'User not found': 'Usuario no encontrado.',
      'You are not registered': 'No estás inscrito en este evento.',
      'Email already registered': 'Este correo electrónico ya está registrado.',
      'Speaker email already in use': 'Este correo electrónico ya está en uso por otro ponente.',
      'Speaker has sessions and cannot be deleted':
        'El ponente tiene sesiones y no se puede eliminar.',
      'Admins cannot demote or deactivate their own account':
        'Los administradores no pueden quitarse el rol ni desactivar su propia cuenta.',
      'end_at must be after start_at': 'La fecha de fin debe ser posterior a la de inicio.',
      'capacity must be at least 1': 'La capacidad debe ser de al menos 1.',
      'start_at must be in the future': 'La fecha de inicio debe estar en el futuro.',
      "session must take place within the event's dates":
        'La sesión debe realizarse dentro de las fechas del evento.',
      'speaker does not exist': 'El ponente no existe.',
      'event dates must still contain all of its existing sessions':
        'Las fechas del evento deben seguir incluyendo todas sus sesiones.',
      'the speaker already has a session in that time slot':
        'El ponente ya tiene una sesión en ese horario.',
      'Only published events accept registrations':
        'Solo los eventos publicados aceptan inscripciones.',
      'The event has already ended': 'El evento ya terminó.',
      'The event is full': 'El evento está lleno.',
      'A finished event does not allow cancelling':
        'Un evento finalizado no permite cancelar la inscripción.',
      'You are already registered to this event': 'Ya estás inscrito en este evento.',
      'The session is full': 'La sesión está llena.',
      'You are already enrolled in this session': 'Ya estás inscrito en esta sesión.',
      'Register to the event before enrolling in a session':
        'Inscríbete al evento antes de inscribirte en una de sus sesiones.',
      'The session overlaps another session you are enrolled in':
        'La sesión se cruza con otra sesión en la que ya estás inscrito.',
      'The session has already ended': 'La sesión ya terminó.',
      'Only sessions of published events accept enrollments':
        'Solo las sesiones de eventos publicados aceptan inscripciones.',
      'You are not enrolled in this session': 'No estás inscrito en esta sesión.',
      'date_to must not be before date_from':
        'La fecha final no puede ser anterior a la fecha inicial.',
    } as Record<string, string>,

    sessionCapacityExceedsEvent: (n: string) =>
      `La capacidad no puede superar la del evento (${n}).`,
    capacityBelowSessions: (n: string) =>
      `La capacidad no puede ser menor que la de la sesión más grande (${n}).`,
    capacityBelowRegistrations: (n: string) =>
      `La capacidad no puede ser menor que las inscripciones actuales (${n}).`,
    eventNotEditable: (status: string) => `Un evento ${status.toLowerCase()} no se puede editar.`,
    statusTransition: (from: string, to: string) =>
      `No se puede cambiar el estado de ${from} a ${to}.`,
    passwordTooShort: (n: string) => `La contraseña debe tener al menos ${n} caracteres.`,

    /**
     * 422 sentences keyed by Pydantic `type`. Each takes the subject ("El campo Nombre" or
     * "Este campo") and the item's `ctx`, and returns null when a number it needs is missing.
     */
    validation: {
      missing: (subject) => `${subject} es obligatorio.`,
      string_too_short: (subject, ctx) =>
        typeof ctx.min_length === 'number'
          ? `${subject} debe tener al menos ${characters(ctx.min_length)}.`
          : null,
      string_too_long: (subject, ctx) =>
        typeof ctx.max_length === 'number'
          ? `${subject} no puede tener más de ${characters(ctx.max_length)}.`
          : null,
      greater_than: (subject, ctx) =>
        typeof ctx.gt === 'number' ? `${subject} debe ser mayor que ${ctx.gt}.` : null,
      greater_than_equal: (subject, ctx) =>
        typeof ctx.ge === 'number' ? `${subject} debe ser mayor o igual que ${ctx.ge}.` : null,
      less_than: (subject, ctx) =>
        typeof ctx.lt === 'number' ? `${subject} debe ser menor que ${ctx.lt}.` : null,
      less_than_equal: (subject, ctx) =>
        typeof ctx.le === 'number' ? `${subject} debe ser menor o igual que ${ctx.le}.` : null,
      int_parsing: (subject) => `${subject} debe ser un número entero.`,
      int_type: (subject) => `${subject} debe ser un número entero.`,
      string_type: (subject) => `${subject} debe ser un texto.`,
      datetime_parsing: (subject) => `${subject} debe ser una fecha y hora válidas.`,
      datetime_type: (subject) => `${subject} debe ser una fecha y hora válidas.`,
      date_parsing: (subject) => `${subject} debe ser una fecha válida.`,
      date_type: (subject) => `${subject} debe ser una fecha válida.`,
      enum: (subject) => `${subject} tiene un valor no permitido.`,
      value_error: (subject) => `${subject} tiene un valor no válido.`,
    } as Record<string, (subject: string, ctx: Record<string, unknown>) => string | null>,
    knownField: (label: string) => `El campo ${label}`,
    unknownField: 'Este campo',
  },

  labels: {
    status: {
      draft: 'Borrador',
      published: 'Publicado',
      cancelled: 'Cancelado',
      finished: 'Finalizado',
    } satisfies Record<EventStatus, string>,
    role: {
      admin: 'Administrador',
      organizer: 'Organizador',
      attendee: 'Asistente',
    } satisfies Record<Role, string>,
  },
}
