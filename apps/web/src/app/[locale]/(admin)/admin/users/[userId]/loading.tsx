import { PageLoading } from "@/components/ui/page-loading";
import { appCopy } from "@/content/copy";

export default function LoadingAdminUserIntegrityPage() {
  return <PageLoading title={appCopy.common.loading} />;
}
