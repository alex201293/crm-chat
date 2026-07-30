"use client";

export default function CrmPage() {
  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Pipeline
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Gestiona tus negocios y oportunidades
          </p>
        </div>
        <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700">
          Nuevo Negocio
        </button>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {["Nuevo Lead", "Contactado", "Calificado", "Cotización", "Negociación", "Ganado"].map(
          (stage) => (
            <div
              key={stage}
              className="w-72 flex-shrink-0 rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
            >
              <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-300">
                {stage}
              </h3>
              <div className="space-y-2">
                <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm dark:border-gray-700 dark:bg-gray-900">
                  <p className="text-xs text-gray-400">Sin negocios en esta etapa</p>
                </div>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
