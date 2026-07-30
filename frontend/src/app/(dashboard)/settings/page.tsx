"use client";

export default function SettingsPage() {
  return (
    <div className="p-6">
      <h2 className="mb-6 text-xl font-semibold text-gray-900 dark:text-gray-100">
        Configuración
      </h2>

      <div className="space-y-6">
        <div className="rounded-lg border border-gray-200 p-6 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-gray-100">
            Organización
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Nombre de la Empresa
              </label>
              <input
                type="text"
                defaultValue="Mi Empresa"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Idioma
              </label>
              <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800">
                <option value="es">Español</option>
                <option value="en">English</option>
              </select>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 p-6 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-gray-100">
            Configuración de IA
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Proveedor de IA
              </label>
              <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800">
                <option value="openai">OpenAI (GPT-4o)</option>
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="google">Google (Gemini)</option>
                <option value="mistral">Mistral</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                API Key
              </label>
              <input
                type="password"
                placeholder="sk-..."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
              />
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 p-6 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-gray-100">
            Widget de Chat
          </h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Color del Widget
              </label>
              <input
                type="color"
                defaultValue="#2563eb"
                className="mt-1 h-10 w-20 rounded border border-gray-300"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Posición
              </label>
              <select className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800">
                <option value="bottom-right">Abajo Derecha</option>
                <option value="bottom-left">Abajo Izquierda</option>
              </select>
            </div>
          </div>
        </div>

        <button className="rounded-lg bg-brand-600 px-6 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-700">
          Guardar Cambios
        </button>
      </div>
    </div>
  );
}
