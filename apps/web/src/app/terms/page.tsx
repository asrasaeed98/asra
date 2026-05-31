import type { Metadata } from "next";
import Link from "next/link";
import { APP_NAME } from "@/lib/app-name";

export const metadata: Metadata = {
  title: `Terms of Service · ${APP_NAME}`,
  description: `Terms of use for ${APP_NAME}.`,
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:py-16">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pink-600">Legal</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-800">Terms of Service</h1>
      <p className="mt-2 text-sm text-stone-500">Last updated: May 31, 2026</p>

      <div className="prose-stone mt-8 space-y-6 text-sm leading-relaxed text-stone-600">
        <p>
          These Terms of Service (&quot;Terms&quot;) govern your use of {APP_NAME} (the
          &quot;Service&quot;), operated by Asra Saeed as an independent project. By using the
          Service, you agree to these Terms. If you do not agree, do not use the Service.
        </p>

        <section>
          <h2 className="text-base font-semibold text-stone-800">What the Service does</h2>
          <p className="mt-2">
            {APP_NAME} helps users explore publicly available datasets and view statistical analysis
            and plain-language summaries. The Service may use automated tools, including AI, to
            explain computed results.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">No professional advice</h2>
          <p className="mt-2">
            The Service is for informational and exploratory purposes only. It does not provide
            financial, investment, medical, legal, regulatory, or policy advice. Do not rely on
            outputs from the Service as your sole basis for important decisions.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Third-party data</h2>
          <p className="mt-2">
            The Service accesses public datasets from third-party providers (such as data.gov, FRED,
            the World Bank, and NYC Open Data). {APP_NAME} is not affiliated with, endorsed by, or
            sponsored by those providers. You are responsible for complying with each dataset&apos;s
            license and attribution requirements when reusing or publishing results.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Accuracy and limitations</h2>
          <p className="mt-2">
            We work to surface trustworthy statistics and link findings to underlying data, but we
            do not guarantee that any output is complete, current, or error-free. Public data may
            contain mistakes, gaps, or bias. Statistical results describe patterns in the data
            analyzed; they do not prove causation. AI-generated summaries and chat responses may
            be incomplete or misinterpret context even when grounded in computed results.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Acceptable use</h2>
          <p className="mt-2">You agree not to:</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Use the Service unlawfully or to harm others</li>
            <li>Attempt to disrupt, overload, scrape, or reverse engineer the Service</li>
            <li>Misrepresent outputs as official statements from data providers or government agencies</li>
            <li>Remove required attribution when sharing or republishing results</li>
          </ul>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Intellectual property</h2>
          <p className="mt-2">
            The Service, including its design, software, and branding (except third-party data and
            trademarks), is owned by the operator. Third-party names, logos, and datasets remain the
            property of their respective owners. &quot;Findings&quot; may be used by other products
            and organizations; nothing in these Terms grants exclusive rights to that name.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Disclaimer of warranties</h2>
          <p className="mt-2">
            THE SERVICE IS PROVIDED &quot;AS IS&quot; AND &quot;AS AVAILABLE&quot; WITHOUT WARRANTIES
            OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING IMPLIED WARRANTIES OF MERCHANTABILITY,
            FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Limitation of liability</h2>
          <p className="mt-2">
            TO THE MAXIMUM EXTENT PERMITTED BY LAW, THE OPERATOR WILL NOT BE LIABLE FOR ANY INDIRECT,
            INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, OR ANY LOSS OF PROFITS, DATA,
            OR GOODWILL, ARISING FROM YOUR USE OF THE SERVICE.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Changes and termination</h2>
          <p className="mt-2">
            We may modify or discontinue the Service or these Terms at any time. Continued use after
            changes means you accept the updated Terms. We may suspend access for conduct that violates
            these Terms or poses risk to the Service.
          </p>
        </section>

        <section>
          <h2 className="text-base font-semibold text-stone-800">Contact</h2>
          <p className="mt-2">
            Questions about these Terms:{" "}
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
        <Link href="/privacy" className="text-pink-600 hover:text-pink-700">
          Privacy Policy
        </Link>
        .
      </p>
    </div>
  );
}
