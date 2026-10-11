import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { beforeEach, describe, expect, it } from "vitest";
import { es } from "../i18n";
import { useAuthStore } from "../store/authStore";
import { ApiError, apiClient, known, normalizeError } from "./client";

let sentConfig: InternalAxiosRequestConfig | undefined;

function respondWith(status: number, data: unknown) {
  apiClient.defaults.adapter = async (config) => {
    sentConfig = config;
    const response = { status, data, statusText: "", headers: {}, config };
    if (status >= 400)
      throw new AxiosError("failed", "ERR_BAD_REQUEST", config, null, response);
    return response;
  };
}

function failWithoutResponse() {
  apiClient.defaults.adapter = async (config) => {
    throw new AxiosError("Network Error", "ERR_NETWORK", config);
  };
}

async function errorOf(request: Promise<unknown>): Promise<ApiError> {
  try {
    await request;
  } catch (error) {
    return error as ApiError;
  }
  throw new Error("request did not fail");
}

beforeEach(() => {
  sentConfig = undefined;
  useAuthStore.setState({ token: null, user: null });
});

describe("apiClient request interceptor", () => {
  it("sends the bearer token when the user is logged in", async () => {
    useAuthStore.setState({ token: "abc" });
    respondWith(200, {});
    await apiClient.get("/events");
    expect(sentConfig?.headers.get("Authorization")).toBe("Bearer abc");
  });

  it("sends no authorization header when the user is logged out", async () => {
    respondWith(200, {});
    await apiClient.get("/events");
    expect(sentConfig?.headers.get("Authorization")).toBeUndefined();
  });
});

describe("apiClient response interceptor", () => {
  it("logs the user out when the backend answers 401", async () => {
    useAuthStore.setState({ token: "expired" });
    respondWith(401, { detail: "Could not validate credentials" });
    const error = await errorOf(apiClient.get("/users/me"));
    expect(error.status).toBe(401);
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("keeps the session when the backend answers 403", async () => {
    useAuthStore.setState({ token: "valid" });
    respondWith(403, { detail: "Insufficient permissions" });
    await errorOf(apiClient.get("/events"));
    expect(useAuthStore.getState().token).toBe("valid");
  });

  it("rejects with an ApiError carrying the network message and no status when the server is unreachable", async () => {
    failWithoutResponse();
    const error = await errorOf(apiClient.get("/events"));
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe(es.common.networkError);
    expect(error.status).toBeNull();
  });

  it("translates a known backend detail to Spanish", async () => {
    respondWith(404, { detail: "Event not found" });
    const error = await errorOf(apiClient.get("/events/9"));
    expect(error.message).toBe("Evento no encontrado.");
    expect(error.status).toBe(404);
  });

  it("uses the generic message for an unknown backend detail", async () => {
    respondWith(409, { detail: "Something brand new happened" });
    const error = await errorOf(apiClient.post("/events"));
    expect(error.message).toBe(es.common.genericError);
    expect(error.status).toBe(409);
  });

  it("uses the generic message when the response has no detail", async () => {
    respondWith(500, {});
    const error = await errorOf(apiClient.get("/events"));
    expect(error.message).toBe(es.common.genericError);
    expect(error.status).toBe(500);
  });
});

describe("known backend details", () => {
  it("maps every key to a non-empty Spanish string different from the key", () => {
    const entries = Object.entries(known);
    expect(entries.length).toBeGreaterThan(0);
    for (const [english, spanish] of entries) {
      expect(spanish.trim()).not.toBe("");
      expect(spanish).not.toBe(english);
    }
  });

  it.each([
    [
      "Could not validate credentials",
      "No se pudieron validar las credenciales. Inicia sesión de nuevo.",
    ],
    [
      "Invalid email or password",
      "Correo electrónico o contraseña incorrectos.",
    ],
    [
      "Insufficient permissions",
      "No tienes permisos para realizar esta acción.",
    ],
    ["Event not found", "Evento no encontrado."],
    ["Session not found", "Sesión no encontrada."],
    ["Speaker not found", "Ponente no encontrado."],
    ["User not found", "Usuario no encontrado."],
    ["You are not registered", "No estás inscrito en este evento."],
    ["Email already registered", "Este correo electrónico ya está registrado."],
    [
      "Speaker email already in use",
      "Este correo electrónico ya está en uso por otro ponente.",
    ],
    [
      "Speaker has sessions and cannot be deleted",
      "El ponente tiene sesiones y no se puede eliminar.",
    ],
    [
      "Admins cannot demote or deactivate their own account",
      "Los administradores no pueden quitarse el rol ni desactivar su propia cuenta.",
    ],
    [
      "end_at must be after start_at",
      "La fecha de fin debe ser posterior a la de inicio.",
    ],
    ["capacity must be at least 1", "La capacidad debe ser de al menos 1."],
    [
      "start_at must be in the future",
      "La fecha de inicio debe estar en el futuro.",
    ],
    [
      "session must take place within the event's dates",
      "La sesión debe realizarse dentro de las fechas del evento.",
    ],
    ["speaker does not exist", "El ponente no existe."],
    [
      "event dates must still contain all of its existing sessions",
      "Las fechas del evento deben seguir incluyendo todas sus sesiones.",
    ],
    [
      "the speaker already has a session in that time slot",
      "El ponente ya tiene una sesión en ese horario.",
    ],
    [
      "Only published events accept registrations",
      "Solo los eventos publicados aceptan inscripciones.",
    ],
    ["The event has already ended", "El evento ya terminó."],
    ["The event is full", "El evento está lleno."],
    [
      "A finished event does not allow cancelling",
      "Un evento finalizado no permite cancelar la inscripción.",
    ],
    [
      "You are already registered to this event",
      "Ya estás inscrito en este evento.",
    ],
  ])('translates "%s"', async (detail, expected) => {
    respondWith(409, { detail });
    const error = await errorOf(apiClient.post("/events"));
    expect(error.message).toBe(expected);
  });
});

describe("parametrized backend details", () => {
  it.each([
    [
      "capacity cannot exceed the event capacity (150)",
      "La capacidad no puede superar la del evento (150).",
    ],
    [
      "capacity cannot be lower than the largest session capacity (40)",
      "La capacidad no puede ser menor que la de la sesión más grande (40).",
    ],
    [
      "capacity cannot be lower than the current registrations (12)",
      "La capacidad no puede ser menor que las inscripciones actuales (12).",
    ],
    [
      "A cancelled event cannot be edited",
      "Un evento cancelado no se puede editar.",
    ],
    [
      "A finished event cannot be edited",
      "Un evento finalizado no se puede editar.",
    ],
    [
      "Cannot change status from draft to finished",
      "No se puede cambiar el estado de Borrador a Finalizado.",
    ],
    [
      "Cannot change status from published to draft",
      "No se puede cambiar el estado de Publicado a Borrador.",
    ],
    [
      "Password must be at least 8 characters long",
      "La contraseña debe tener al menos 8 caracteres.",
    ],
  ])('translates "%s"', async (detail, expected) => {
    respondWith(409, { detail });
    const error = await errorOf(apiClient.post("/events"));
    expect(error.message).toBe(expected);
  });

  it("uses the generic message when a status in the pattern is not a known status", async () => {
    respondWith(409, { detail: "Cannot change status from draft to archived" });
    const error = await errorOf(apiClient.post("/events"));
    expect(error.message).toBe(es.common.genericError);
  });
});

describe("422 validation errors", () => {
  async function messageFor(item: Record<string, unknown>) {
    respondWith(422, { detail: [item] });
    return (await errorOf(apiClient.post("/events"))).message;
  }

  it.each([
    [{ loc: ["body", "name"], type: "missing" }, "Nombre: Campo obligatorio"],
    [
      {
        loc: ["body", "name"],
        type: "string_too_short",
        ctx: { min_length: 1 },
      },
      "Nombre: Longitud mínima: 1",
    ],
    [
      {
        loc: ["body", "password"],
        type: "string_too_short",
        ctx: { min_length: 8 },
      },
      "Contraseña: Longitud mínima: 8",
    ],
    [
      {
        loc: ["body", "name"],
        type: "string_too_long",
        ctx: { max_length: 200 },
      },
      "Nombre: Longitud máxima: 200",
    ],
    [
      { loc: ["body", "capacity"], type: "greater_than", ctx: { gt: 0 } },
      "Capacidad: Debe ser mayor que 0",
    ],
    [
      { loc: ["body", "capacity"], type: "greater_than_equal", ctx: { ge: 1 } },
      "Capacidad: Debe ser mayor o igual que 1",
    ],
    [
      { loc: ["query", "size"], type: "less_than", ctx: { lt: 101 } },
      "Tamaño: Debe ser menor que 101",
    ],
    [
      { loc: ["query", "size"], type: "less_than_equal", ctx: { le: 100 } },
      "Tamaño: Debe ser menor o igual que 100",
    ],
    [
      { loc: ["query", "page"], type: "int_parsing" },
      "Página: Debe ser un número entero",
    ],
    [
      { loc: ["body", "capacity"], type: "int_type" },
      "Capacidad: Debe ser un número entero",
    ],
    [
      { loc: ["body", "name"], type: "string_type" },
      "Nombre: Debe ser un texto",
    ],
    [
      { loc: ["body", "start_at"], type: "datetime_parsing" },
      "Inicio: Debe ser una fecha y hora válidas",
    ],
    [
      { loc: ["body", "end_at"], type: "datetime_type" },
      "Fin: Debe ser una fecha y hora válidas",
    ],
    [{ loc: ["query", "status"], type: "enum" }, "Valor no permitido"],
    [
      { loc: ["body", "email"], type: "value_error" },
      "Correo electrónico: Valor no válido",
    ],
  ])("translates %j", async (item, expected) => {
    expect(await messageFor(item)).toBe(expected);
  });

  it("shows the bare translation for an item whose field has no label", async () => {
    expect(
      await messageFor({ loc: ["body", "unlisted"], type: "missing" }),
    ).toBe("Campo obligatorio");
  });

  it("never shows the raw English message of an unknown type", async () => {
    const message = await messageFor({
      loc: ["body", "name"],
      msg: "Something odd",
      type: "brand_new_type",
    });
    expect(message).toBe("Nombre: Valor no válido");
  });

  it("uses the generic invalid value text when the context lacks the expected number", async () => {
    expect(
      await messageFor({ loc: ["body", "name"], type: "string_too_short" }),
    ).toBe("Nombre: Valor no válido");
  });

  it("uses the generic invalid value text when the item has no type", async () => {
    expect(await messageFor({ msg: "whatever" })).toBe("Valor no válido");
  });

  it("joins several items with a period", async () => {
    respondWith(422, {
      detail: [
        { loc: ["body", "email"], type: "value_error" },
        {
          loc: ["body", "capacity"],
          type: "greater_than_equal",
          ctx: { ge: 1 },
        },
      ],
    });
    const error = await errorOf(apiClient.post("/events"));
    expect(error.message).toBe(
      "Correo electrónico: Valor no válido. Capacidad: Debe ser mayor o igual que 1",
    );
  });
});

describe("normalizeError", () => {
  it("returns an ApiError untouched", () => {
    const original = new ApiError("x", 400);
    expect(normalizeError(original)).toBe(original);
  });

  it("maps an unknown thrown value to the generic message", () => {
    expect(normalizeError(new Error("boom")).message).toBe(
      es.common.genericError,
    );
  });
});
