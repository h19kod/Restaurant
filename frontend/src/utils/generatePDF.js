import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

export function generateInvoicePDF(invoice, order) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a5' })
  const pageWidth = doc.internal.pageSize.getWidth()

  // ── Header ──────────────────────────────────────────────────────────────────
  doc.setFillColor(37, 99, 235)
  doc.rect(0, 0, pageWidth, 30, 'F')

  doc.setTextColor(255, 255, 255)
  doc.setFontSize(16)
  doc.setFont('helvetica', 'bold')
  doc.text('Restaurant Management System', pageWidth / 2, 12, { align: 'center' })
  doc.setFontSize(10)
  doc.setFont('helvetica', 'normal')
  doc.text('Tax Invoice / فاتورة ضريبية', pageWidth / 2, 20, { align: 'center' })

  // ── Invoice Info ─────────────────────────────────────────────────────────────
  doc.setTextColor(40, 40, 40)
  doc.setFontSize(9)

  const leftX  = 14
  const rightX = pageWidth - 14
  let   y      = 38

  const addRow = (label, value, bold = false) => {
    doc.setFont('helvetica', bold ? 'bold' : 'normal')
    doc.text(label, leftX, y)
    doc.text(String(value), rightX, y, { align: 'right' })
    y += 6
  }

  addRow('Invoice #:', invoice.id, true)
  addRow('Order #:', invoice.order_id)
  addRow('Table:', order?.table_id ? `Table ${order.table_id}` : '—')
  addRow('Date:', new Date(invoice.paid_at).toLocaleDateString('en', { day: '2-digit', month: 'short', year: 'numeric' }))
  addRow('Time:', new Date(invoice.paid_at).toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }))
  addRow('Payment:', invoice.payment_method)

  // ── Divider ──────────────────────────────────────────────────────────────────
  y += 2
  doc.setDrawColor(200, 200, 200)
  doc.line(leftX, y, rightX, y)
  y += 6

  // ── Items Table ──────────────────────────────────────────────────────────────
  const items = order?.order_items?.map(i => [
    i.menu_item?.name || `Item #${i.menu_item_id}`,
    i.quantity,
    `${Number(i.ordered_price).toFixed(2)} SAR`,
    `${Number(i.ordered_price * i.quantity).toFixed(2)} SAR`,
  ]) || []

  autoTable(doc, {
    startY: y,
    head: [['Item', 'Qty', 'Unit Price', 'Total']],
    body: items,
    theme: 'striped',
    headStyles: { fillColor: [37, 99, 235], fontSize: 8, fontStyle: 'bold' },
    bodyStyles: { fontSize: 8 },
    margin: { left: leftX, right: 14 },
    columnStyles: {
      0: { cellWidth: 'auto' },
      1: { halign: 'center', cellWidth: 15 },
      2: { halign: 'right', cellWidth: 28 },
      3: { halign: 'right', cellWidth: 28 },
    },
  })

  y = doc.lastAutoTable.finalY + 6

  // ── Totals ───────────────────────────────────────────────────────────────────
  doc.setFillColor(248, 250, 252)
  doc.rect(leftX, y, pageWidth - 28, 30, 'F')

  const totY = y + 6
  doc.setFontSize(8)
  doc.setFont('helvetica', 'normal')
  doc.setTextColor(80, 80, 80)

  doc.text('Subtotal:', leftX + 3, totY)
  doc.text(`${Number(invoice.subtotal).toFixed(2)} SAR`, rightX - 3, totY, { align: 'right' })

  doc.text('Tax (15%):', leftX + 3, totY + 6)
  doc.text(`${Number(invoice.tax_amount).toFixed(2)} SAR`, rightX - 3, totY + 6, { align: 'right' })

  if (Number(invoice.discount_amount) > 0) {
    doc.setTextColor(22, 163, 74)
    doc.text('Discount:', leftX + 3, totY + 12)
    doc.text(`-${Number(invoice.discount_amount).toFixed(2)} SAR`, rightX - 3, totY + 12, { align: 'right' })
    doc.setTextColor(80, 80, 80)
  }

  doc.setDrawColor(200, 200, 200)
  doc.line(leftX + 3, totY + 15, rightX - 3, totY + 15)

  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.setTextColor(37, 99, 235)
  doc.text('TOTAL:', leftX + 3, totY + 22)
  doc.text(`${Number(invoice.total_amount).toFixed(2)} SAR`, rightX - 3, totY + 22, { align: 'right' })

  // ── Footer ───────────────────────────────────────────────────────────────────
  const footerY = doc.internal.pageSize.getHeight() - 12
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(7)
  doc.setTextColor(150, 150, 150)
  doc.text('Thank you for dining with us! | شكراً لزيارتكم', pageWidth / 2, footerY, { align: 'center' })

  doc.save(`invoice-${invoice.id}.pdf`)
}
