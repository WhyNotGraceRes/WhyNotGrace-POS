import { apiClient } from "@/api/client";

/**
 * Prints a server-rendered receipt through the browser.
 *
 * The HTML is fetched rather than built here, so the paper and the thermal
 * output come from one document — see the backend's receipt package. A
 * client that assembled its own layout would inevitably drift from what the
 * printer produces, and the two disagreeing about what a guest paid is the
 * exact failure this design exists to prevent.
 *
 * A hidden iframe rather than a popup window: popups get blocked, and a
 * blocked print is a cashier standing at a counter wondering why nothing
 * happened. The iframe is removed after printing, but only once the dialog
 * has closed — removing it earlier cancels the print on some browsers.
 */
export async function printHtmlDocument(html: string): Promise<void> {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  // Off-screen rather than display:none — a hidden frame has no layout in
  // some browsers, and printing an unlaid-out document produces a blank page.
  frame.style.position = "fixed";
  frame.style.right = "100%";
  frame.style.bottom = "100%";
  frame.style.width = "80mm";
  frame.style.height = "0";
  frame.style.border = "0";
  document.body.appendChild(frame);

  const doc = frame.contentDocument;
  if (!doc) {
    frame.remove();
    throw new Error("Could not open a print frame");
  }

  doc.open();
  doc.write(html);
  doc.close();

  await new Promise<void>((resolve) => {
    const go = () => {
      try {
        frame.contentWindow?.focus();
        frame.contentWindow?.print();
      } finally {
        // The dialog is modal, so this runs after it closes on most
        // browsers; the timeout covers the ones where it does not.
        window.setTimeout(() => {
          frame.remove();
          resolve();
        }, 500);
      }
    };
    if (frame.contentWindow?.document.readyState === "complete") go();
    else frame.onload = go;
  });
}

/**
 * Prints a bill and counts it. The server decides whether this copy is a
 * duplicate and stamps the output accordingly — the client never makes that
 * call, so forgetting to ask cannot produce an unmarked second original.
 */
export async function printBill(billId: string): Promise<void> {
  const { data } = await apiClient.post<string>(
    `/billing/${billId}/print-receipt`,
    null,
    { params: { format: "html" }, responseType: "text" }
  );
  await printHtmlDocument(data);
}

/** Renders the bill without counting it as a print. */
export async function previewBill(billId: string): Promise<string> {
  const { data } = await apiClient.get<string>(`/billing/${billId}/receipt`, {
    params: { format: "html" },
    responseType: "text",
  });
  return data;
}

/** Prints one kitchen ticket. Pass a station to print only its items. */
export async function printKotTicket(kotId: string, station?: string): Promise<void> {
  const { data } = await apiClient.get<string>(`/kot/${kotId}/ticket`, {
    params: { format: "html", ...(station ? { station } : {}) },
    responseType: "text",
  });
  await printHtmlDocument(data);
}

/**
 * Prints one ticket per station this order touches, so the tandoor and the
 * Chinese counter each get only their own items. A business that has not
 * configured stations gets a single ticket, because the backend reports one
 * empty-string station in that case.
 */
export async function printKotForAllStations(kotId: string): Promise<number> {
  const { data: stations } = await apiClient.get<string[]>(`/kot/${kotId}/stations`);
  const targets = stations.length ? stations : [""];
  for (const station of targets) {
    await printKotTicket(kotId, station || undefined);
  }
  return targets.length;
}
