"use client";

export default function DashboardPage() {
  return (
    <div className="p-6">
      <h2 className="mb-6 text-xl font-semibold text-gray-900 dark:text-gray-100">
        Panel de Control
      </h2>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Conversaciones Activas", value: "0" },
          { label: "Contactos", value: "0" },
          { label: "Negocios Abiertos", value: "$0" },
          { label: "Atendidos por IA", value: "0%" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-700 dark:bg-gray-800"
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-lg border border-gray-200 p-6 dark:border-gray-700">
        <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-gray-100">
          Actividad Reciente
        </h3>
        <p className="text-gray-500 dark:text-gray-400">
          Sin actividad aún. Comienza a chatear o crea negocios para ver métricas aquí.
        </p>
      </div>
    </div>
  );
}
