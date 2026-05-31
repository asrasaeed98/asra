import type { Metadata } from "next";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export const metadata: Metadata = {
  title: `Privacy Policy · ${APP_NAME}`,
  description: `Privacy policy for ${APP_NAME}.`,
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:py-16">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-600">Legal</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800">Privacy Policy</h1>
      <p className="mt-2 text-sm text-stone-500">Last updated: May 31, 2026</p>

      <div className="mt-8 space-y-6 text-sm leading-relaxed text-stone-600">
        <p>
          This Privacy Policy describes how {APP_NAME} (&quot;we&quot;, &quot;us&quot;) handles
          information when you use our website and analysis tools. {APP_NAME} is operated by Asra
          Saeed as an independent project.
        </p>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Information we collect</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5">
            <li>
              <strong className="font-medium text-stone-700">Analysis sessions:</strong> dataset
              selections, optional research questions, analysis configuration, and generated results
              stored to run and display your session.
            </li>
            <li>
              <strong className="font-medium text-stone-700">Chat messages:</strong> questions you
              submit in the grounded chat feature, stored with your session to provide replies.
            </li>
            <li>
              <strong className="font-medium text-stone-700">Technical logs:</strong> basic server
              logs (such as IP address, browser type, timestamps, and error information) needed to
              operate and secure the Service.
            </li>
          </ul>
          <p className="mt-2">
            We do not require account registration for basic use. We do not knowingly collect
            information from children under 13.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">How we use information</h2>
          <ul className="mt-2 list-disc space-y-1.5 pl-5">
            <li>Run statistical analysis and display results</li>
            <li>Generate AI summaries and chat responses grounded in your results</li>
            <li>Maintain, debug, and improve the Service</li>
            <li>Monitor usage costs and prevent abuse</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Third-party services</h2>
          <p className="mt-2">
            We use third-party infrastructure and APIs to operate {APP_NAME}, including:
          </p>
          <ul className="mt-2 list-disc space-y-1.5 pl-5">
            <li>
              <strong className="font-medium text-stone-700">Anthropic</strong> for AI-generated
              summaries and chat. Your analysis context and chat questions may be sent to Anthropic
              to generate responses. See{" "}
              <a
                href="https://www.anthropic.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-pink-600 hover:text-pink-700"
              >
                Anthropic&apos;s Privacy Policy
              </a>
              .
            </li>
            <li>
              <strong className="font-medium text-stone-700">Hosting providers</strong> (such as
              Railway and Vercel) that store and serve the application and database.
            </li>
            <li>
              <strong className="font-medium text-stone-700">Public data APIs</strong> when you
              select datasets for analysis. Those providers receive requests necessary to fetch data.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Cookies and local storage</h2>
          <p className="mt-2">
            The Service may use minimal browser storage or cookies required for basic functionality.
            We do not use third-party advertising cookies.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Retention</h2>
          <p className="mt-2">
            Analysis sessions and related data are retained for a limited period to support your
            results page and operational needs. We may delete old sessions periodically. Server logs
            are retained for a shorter operational window.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Your choices</h2>
          <p className="mt-2">
            Do not submit sensitive personal information in research questions or chat. If you have
            questions about data we hold about a session, contact us using the link below.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Changes</h2>
          <p className="mt-2">
            We may update this Privacy Policy from time to time. The &quot;Last updated&quot; date
            at the top will reflect the latest version.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Contact</h2>
          <p className="mt-2">
            Privacy questions:{" "}
            <a
              href="https://www.linkedin.com/in/asrasaeed/"
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-pink-600 hover:text-pink-700"
            >
              contact via LinkedIn
            </a>
            .
          </p>
        </section>
      </div>

      <p className="mt-10 text-xs text-stone-400">
        See also our{" "}
        <Link href="/terms" className="text-pink-600 hover:text-pink-700">
          Terms of Service
        </Link>
        .
      </p>
    </div>
  );
}
