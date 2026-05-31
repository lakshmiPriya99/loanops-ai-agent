import { LoanWorkspace } from "../components/LoanWorkspace";
import { fetchLoans } from "../lib/api";

export default async function Home() {
  const loans = await fetchLoans();
  return <LoanWorkspace loans={loans} />;
}
