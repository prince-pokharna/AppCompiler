"""Next.js project generator — produces a complete project from CompletedAppSchema."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.app_schema import CompletedAppSchema

logger = logging.getLogger("appcompiler.codegen.nextjs")

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_jinja_env() -> Environment:
    """Create a Jinja2 environment with the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape([]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def generate_nextjs_project(schema: CompletedAppSchema) -> dict[str, str]:
    """Generate a complete Next.js project from the schema.

    Returns:
        Dict mapping file paths to file contents.
    """
    files: dict[str, str] = {}
    env = _get_jinja_env()

    # package.json
    files["package.json"] = _generate_package_json(schema)

    # Prisma schema
    files["prisma/schema.prisma"] = _generate_prisma_schema(schema)

    # App layout
    files["src/app/layout.tsx"] = _generate_layout(schema, env)

    # Pages
    for page in schema.ui.pages:
        route = page.route.strip("/")
        if not route:
            route = ""
        path = f"src/app/{route}/page.tsx" if route else "src/app/page.tsx"
        files[path] = _generate_page(schema, page, env)

    # API routes
    api_groups: dict[str, list] = {}
    for endpoint in schema.api.endpoints:
        group = endpoint.group or "general"
        api_groups.setdefault(group, []).append(endpoint)

    for group, endpoints in api_groups.items():
        files[f"src/app/api/{group}/route.ts"] = _generate_api_route(group, endpoints, env)

    # Middleware
    files["src/middleware.ts"] = _generate_middleware(schema, env)

    # Auth config
    files["src/lib/auth.ts"] = _generate_auth_config(schema)

    # Prisma client
    files["src/lib/prisma.ts"] = _generate_prisma_client()

    # Type definitions
    files["src/types/index.ts"] = _generate_types(schema)

    # Tailwind config
    files["tailwind.config.ts"] = _generate_tailwind_config()

    # tsconfig
    files["tsconfig.json"] = _generate_tsconfig()

    # .env.example
    files[".env.example"] = _generate_env_example(schema)

    logger.info(f"Generated {len(files)} project files")
    return files


def _generate_package_json(schema: CompletedAppSchema) -> str:
    """Generate package.json with all required dependencies."""
    pkg = {
        "name": schema.meta.app_name.lower().replace(" ", "-"),
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint",
            "postinstall": "prisma generate",
        },
        "dependencies": {
            "next": "14.2.0",
            "react": "^18.3.0",
            "react-dom": "^18.3.0",
            "@prisma/client": "^5.20.0",
            "next-auth": "^4.24.0",
            "bcryptjs": "^2.4.3",
            "zod": "^3.23.0",
            "tailwindcss": "^3.4.0",
            "autoprefixer": "^10.4.0",
            "postcss": "^8.4.0",
        },
        "devDependencies": {
            "typescript": "^5.5.0",
            "@types/node": "^20.14.0",
            "@types/react": "^18.3.0",
            "@types/react-dom": "^18.3.0",
            "@types/bcryptjs": "^2.4.6",
            "prisma": "^5.20.0",
            "eslint": "^8.57.0",
            "eslint-config-next": "14.2.0",
        },
    }

    if schema.intent.payment_required:
        pkg["dependencies"]["stripe"] = "^14.0.0"
        pkg["dependencies"]["@stripe/stripe-js"] = "^2.4.0"

    return json.dumps(pkg, indent=2)


def _generate_prisma_schema(schema: CompletedAppSchema) -> str:
    """Generate Prisma schema from DatabaseSchema."""
    lines = [
        "generator client {",
        '  provider = "prisma-client-js"',
        "}",
        "",
        "datasource db {",
        '  provider = "postgresql"',
        '  url      = env("DATABASE_URL")',
        "}",
        "",
    ]

    type_map = {
        "String": "String",
        "Integer": "Int",
        "Boolean": "Boolean",
        "DateTime": "DateTime",
        "Text": "String",
        "Float": "Float",
        "JSON": "Json",
        "UUID": "String",
    }

    for table in schema.database.tables:
        model_name = _to_pascal_case(table.name)
        lines.append(f"model {model_name} {{")

        for col in table.columns:
            prisma_type = type_map.get(col.type, "String")
            parts = [f"  {col.name}"]

            if col.primary_key:
                parts.append(prisma_type)
                if col.type == "UUID":
                    parts.append('@id @default(uuid())')
                else:
                    parts.append("@id @default(autoincrement())")
            else:
                nullable = "?" if col.nullable and not col.primary_key else ""
                parts.append(f"{prisma_type}{nullable}")

                attrs = []
                if col.unique:
                    attrs.append("@unique")
                if col.default:
                    if col.default in ("now()", "gen_random_uuid()"):
                        attrs.append("@default(now())" if "now" in col.default else "@default(uuid())")
                    elif col.default in ("true", "false"):
                        attrs.append(f"@default({col.default})")
                    elif col.default.isdigit():
                        attrs.append(f"@default({col.default})")

                if attrs:
                    parts.extend(attrs)

            lines.append(" ".join(parts))

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def _generate_layout(schema: CompletedAppSchema, env: Environment) -> str:
    """Generate root layout."""
    app_name = schema.meta.app_name
    return f'''import type {{ Metadata }} from "next";
import "./globals.css";

export const metadata: Metadata = {{
  title: "{app_name}",
  description: "{schema.meta.description}",
}};

export default function RootLayout({{
  children,
}}: Readonly<{{
  children: React.ReactNode;
}}>) {{
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 antialiased">
        {{children}}
      </body>
    </html>
  );
}}
'''


def _generate_page(schema: CompletedAppSchema, page, env: Environment) -> str:
    """Generate a page component."""
    components_jsx = []
    for comp in page.components:
        comp_name = comp.name.replace(" ", "")
        if comp.type == "stats":
            components_jsx.append(f'        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">\n          <div className="bg-white p-6 rounded-lg shadow"><h3 className="text-sm font-medium text-gray-500">Total</h3><p className="text-2xl font-bold">0</p></div>\n        </div>')
        elif comp.type == "table":
            components_jsx.append(f'        <div className="bg-white rounded-lg shadow overflow-hidden">\n          <table className="min-w-full divide-y divide-gray-200">\n            <thead className="bg-gray-50"><tr><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th></tr></thead>\n            <tbody className="divide-y divide-gray-200"><tr><td className="px-6 py-4 text-sm text-gray-500" colSpan={{2}}>No data yet</td></tr></tbody>\n          </table>\n        </div>')
        elif comp.type == "form":
            components_jsx.append(f'        <div className="bg-white p-6 rounded-lg shadow">\n          <h3 className="text-lg font-semibold mb-4">{comp.name}</h3>\n          <form className="space-y-4">\n            <div><label className="block text-sm font-medium text-gray-700">Name</label><input type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" /></div>\n            <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded-md hover:bg-indigo-700">Submit</button>\n          </form>\n        </div>')
        elif comp.type == "chart":
            components_jsx.append(f'        <div className="bg-white p-6 rounded-lg shadow">\n          <h3 className="text-lg font-semibold mb-4">{comp.name}</h3>\n          <div className="h-64 flex items-center justify-center text-gray-400">Chart placeholder</div>\n        </div>')
        else:
            components_jsx.append(f'        <div className="bg-white p-6 rounded-lg shadow">\n          <h3 className="text-lg font-semibold">{comp.name}</h3>\n          <p className="text-gray-500">{comp.description}</p>\n        </div>')

    body = "\n".join(components_jsx) if components_jsx else '        <p className="text-gray-500">Page content</p>'
    auth_check = ""
    if page.auth_required:
        auth_check = '\n  // Auth check would go here'

    return f'''export default function {_to_pascal_case(page.name)}Page() {{{auth_check}
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">{page.name}</h1>
{body}
      </div>
    </main>
  );
}}
'''


def _generate_api_route(group: str, endpoints: list, env: Environment) -> str:
    """Generate API route handlers for an endpoint group."""
    handlers = []
    methods_seen: set[str] = set()

    for ep in endpoints:
        method = ep.method.upper()
        if method in methods_seen:
            continue
        methods_seen.add(method)

        handlers.append(f'''export async function {method}(request: Request) {{
  try {{
    // {ep.description}
    const data = {method in ("POST", "PUT", "PATCH") and "await request.json()" or "null"};
    return Response.json({{ success: true, data: [] }});
  }} catch (error) {{
    return Response.json({{ success: false, error: "Internal server error" }}, {{ status: 500 }});
  }}
}}''')

    return f'''import {{ NextResponse }} from "next/server";

{chr(10).join(handlers)}
'''


def _generate_middleware(schema: CompletedAppSchema, env: Environment) -> str:
    """Generate Next.js middleware for auth."""
    protected = [
        f'"{p.route}"' for p in schema.ui.pages if p.auth_required
    ]
    paths_str = ", ".join(protected) if protected else '"/dashboard"'

    return f'''import {{ NextResponse }} from "next/server";
import type {{ NextRequest }} from "next/server";

const protectedPaths = [{paths_str}];

export function middleware(request: NextRequest) {{
  const {{ pathname }} = request.nextUrl;
  const isProtected = protectedPaths.some((path) => pathname.startsWith(path));

  if (isProtected) {{
    const token = request.cookies.get("next-auth.session-token")?.value;
    if (!token) {{
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }}
  }}

  return NextResponse.next();
}}

export const config = {{
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}};
'''


def _generate_auth_config(schema: CompletedAppSchema) -> str:
    """Generate NextAuth configuration."""
    return '''import NextAuth, { type NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { compare } from "bcryptjs";
import { prisma } from "./prisma";

export const authOptions: NextAuthOptions = {
  session: { strategy: "jwt" },
  pages: { signIn: "/login" },
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await prisma.user.findUnique({
          where: { email: credentials.email },
        });

        if (!user || !user.password_hash) return null;

        const isValid = await compare(credentials.password, user.password_hash);
        if (!isValid) return null;

        return { id: user.id, email: user.email, name: user.name, role: user.role };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = (user as Record<string, unknown>).role;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as Record<string, unknown>).role = token.role;
      }
      return session;
    },
  },
};

export default NextAuth(authOptions);
'''


def _generate_prisma_client() -> str:
    """Generate Prisma client singleton."""
    return '''import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const prisma = globalForPrisma.prisma || new PrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
'''


def _generate_types(schema: CompletedAppSchema) -> str:
    """Generate TypeScript type definitions."""
    lines = ['// Auto-generated type definitions', '']

    for table in schema.database.tables:
        type_name = _to_pascal_case(table.name)
        lines.append(f"export interface {type_name} {{")
        ts_type_map = {
            "String": "string", "Integer": "number", "Boolean": "boolean",
            "DateTime": "string", "Text": "string", "Float": "number",
            "JSON": "Record<string, unknown>", "UUID": "string",
        }
        for col in table.columns:
            ts_type = ts_type_map.get(col.type, "string")
            optional = "?" if col.nullable else ""
            lines.append(f"  {col.name}{optional}: {ts_type};")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def _generate_tailwind_config() -> str:
    return '''import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: {} },
  plugins: [],
};
export default config;
'''


def _generate_tsconfig() -> str:
    return json.dumps({
        "compilerOptions": {
            "target": "es5", "lib": ["dom", "dom.iterable", "esnext"],
            "allowJs": True, "skipLibCheck": True, "strict": True,
            "noEmit": True, "esModuleInterop": True,
            "module": "esnext", "moduleResolution": "bundler",
            "resolveJsonModule": True, "isolatedModules": True,
            "jsx": "preserve", "incremental": True,
            "plugins": [{"name": "next"}],
            "paths": {"@/*": ["./src/*"]},
        },
        "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
        "exclude": ["node_modules"],
    }, indent=2)


def _generate_env_example(schema: CompletedAppSchema) -> str:
    lines = [
        "DATABASE_URL=postgresql://user:password@localhost:5432/dbname",
        "NEXTAUTH_SECRET=your-secret-here",
        "NEXTAUTH_URL=http://localhost:3000",
    ]
    if schema.intent.payment_required:
        lines.extend(["STRIPE_SECRET_KEY=sk_test_...", "STRIPE_PUBLISHABLE_KEY=pk_test_..."])
    return "\n".join(lines) + "\n"


def _to_pascal_case(name: str) -> str:
    """Convert a string to PascalCase."""
    clean = name.replace("-", " ").replace("_", " ").replace("/", " ")
    return "".join(word.capitalize() for word in clean.split() if word)
