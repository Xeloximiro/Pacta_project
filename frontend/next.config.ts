import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Em desenvolvimento o navegador chama `/api/...` na própria origem e o Next
    // encaminha para o FastAPI. Reproduz o arranjo de produção, em que o nginx faz esse
    // proxy — mesma origem nos dois ambientes, portanto nenhum CORS a configurar e nada
    // de "funciona local, quebra no deploy" por diferença de origem.
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL ?? "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
