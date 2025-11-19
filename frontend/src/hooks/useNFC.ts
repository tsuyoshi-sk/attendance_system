import { useState, useCallback } from 'react';

interface NFCError {
  message: string;
  code?: string;
}

export const useNFC = () => {
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<NFCError | null>(null);

  const checkNFCSupport = useCallback(() => {
    if (!('NDEFReader' in window)) {
      return {
        supported: false,
        message: 'このブラウザはWeb NFC APIに対応していません。Chrome for Androidをご利用ください。',
      };
    }
    return { supported: true, message: '' };
  }, []);

  const scanNFC = useCallback(async (): Promise<string | null> => {
    const support = checkNFCSupport();
    if (!support.supported) {
      setError({ message: support.message });
      return null;
    }

    try {
      setIsScanning(true);
      setError(null);

      // @ts-ignore - Web NFC API types
      const ndef = new NDEFReader();

      // スキャンを開始
      await ndef.scan();
      console.log('NFCスキャン開始...');

      return new Promise((resolve, reject) => {
        // タイムアウト設定（30秒）
        const timeout = setTimeout(() => {
          setIsScanning(false);
          reject(new Error('スキャンがタイムアウトしました'));
        }, 30000);

        // @ts-ignore
        ndef.addEventListener('reading', ({ serialNumber }) => {
          clearTimeout(timeout);
          setIsScanning(false);

          // シリアル番号を16進数文字列に変換
          const hexId = serialNumber.replace(/:/g, '').toUpperCase();
          console.log('NFC読み取り成功:', hexId);
          resolve(hexId);
        });

        // @ts-ignore
        ndef.addEventListener('readingerror', () => {
          clearTimeout(timeout);
          setIsScanning(false);
          reject(new Error('NFCカードの読み取りに失敗しました'));
        });
      });
    } catch (err: any) {
      setIsScanning(false);
      const errorMessage = err.message || 'NFCスキャンエラーが発生しました';
      setError({ message: errorMessage, code: err.name });
      console.error('NFC scan error:', err);
      return null;
    }
  }, [checkNFCSupport]);

  const cancelScan = useCallback(() => {
    setIsScanning(false);
    setError(null);
  }, []);

  return {
    isScanning,
    error,
    scanNFC,
    cancelScan,
    checkNFCSupport,
  };
};
