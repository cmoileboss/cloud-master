import { Button } from '@mantine/core';
import type { ButtonProps } from '@mantine/core';
import { useMutation } from '@tanstack/react-query';
import { IconDownload } from '@tabler/icons-react';
import { downloadPdf, showError } from '../api';
import type { ConvocationDocument } from '../types';

export default function DownloadButton({
  document,
  ...props
}: { document: ConvocationDocument } & ButtonProps) {
  const download = useMutation({
    mutationFn: () => downloadPdf(document.id, `convocation-${document.meeting_date}.pdf`),
    onError: showError,
  });
  return (
    <Button
      leftSection={<IconDownload size={16} />}
      loading={download.isPending}
      onClick={() => download.mutate()}
      {...props}
    >
      Télécharger le PDF
    </Button>
  );
}
