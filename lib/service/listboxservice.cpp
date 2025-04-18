#include <lib/service/listboxservice.h>
#include <lib/base/esimpleconfig.h>
#include <lib/service/service.h>
#include <lib/gdi/font.h>
#include <lib/gdi/epng.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/db.h>
#include <lib/dvb/pmt.h>
//////// OPENSPA [morser] Add picons for service quality  ////////////
#include <lib/dvb/db.h>
#include <lib/base/nconfig.h>
//////////////////////////////////////////////////////////////////////
#include <lib/nav/core.h>
#include <lib/python/connections.h>
#include <lib/python/python.h>
#include <ctype.h>

ePyObject eListboxServiceContent::m_GetPiconNameFunc;

void eListboxServiceContent::addService(const eServiceReference &service, bool beforeCurrent)
{
	if (beforeCurrent && m_size)
		m_list.insert(m_cursor, service);
	else
		m_list.push_back(service);
	if (m_size++)
	{
		++m_cursor_number;
		if (m_listbox)
			m_listbox->entryAdded(cursorResolve(m_cursor_number-1));
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number=0;
		m_listbox->entryAdded(0);
	}
}

void eListboxServiceContent::removeCurrent()
{
	if (m_size && m_listbox)
	{
		if (m_cursor_number == --m_size)
		{
			m_list.erase(m_cursor--);
			if (m_size)
			{
				--m_cursor_number;
				m_listbox->entryRemoved(cursorResolve(m_cursor_number+1));
			}
			else
				m_listbox->entryRemoved(cursorResolve(m_cursor_number));
		}
		else
		{
			m_list.erase(m_cursor++);
			m_listbox->entryRemoved(cursorResolve(m_cursor_number));
		}

		// prevent a crash in case we are deleting an marked item while in move mode
		m_current_marked = false;
	}
}

void eListboxServiceContent::FillFinished()
{
	m_size = m_list.size();
	cursorHome();

	if (m_listbox)
		m_listbox->entryReset();
}

void eListboxServiceContent::setRoot(const eServiceReference &root, bool justSet)
{
	m_list.clear();
	m_cursor = m_list.end();
	m_root = root;

	if (justSet)
	{
		m_lst=0;
		return;
	}
	ASSERT(m_service_center);

	if (m_service_center->list(m_root, m_lst))
		eDebug("[eListboxServiceContent] no list available!");
	else if (m_lst->getContent(m_list))
		eDebug("[eListboxServiceContent] getContent failed");

	FillFinished();
}

bool eListboxServiceContent::setCurrent(const eServiceReference &ref)
{
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
	{
		if ( *i == ref )
		{
			m_cursor = i;
			m_cursor_number = index;
			if (m_listbox)
			{
				m_listbox->moveSelectionTo(cursorResolve(index));
				return true;
			}
			break;
		}
	}
	return false;
}

void eListboxServiceContent::getCurrent(eServiceReference &ref)
{
	if (cursorValid())
		ref = *m_cursor;
	else
		ref = eServiceReference();
}

void eListboxServiceContent::getPrev(eServiceReference &ref)
{
	if (cursorValid())
	{
		list::iterator cursor(m_cursor);
		if (cursor == m_list.begin())
		{
			cursor = m_list.end();
		}
		ref = *(--cursor);
	}
	else
		ref = eServiceReference();
}

void eListboxServiceContent::getNext(eServiceReference &ref)
{
	if (cursorValid())
	{
		list::iterator cursor(m_cursor);
		cursor++;
		if (cursor == m_list.end())
		{
			cursor = m_list.begin();
		}
 		ref = *(cursor);
	}
	else
		ref = eServiceReference();
}

PyObject *eListboxServiceContent::getList()
{
	ePyObject result = PyList_New(m_list.size());
	int pos=0;
	for (list::iterator it(m_list.begin()); it != m_list.end(); ++it)
	{
		PyList_SET_ITEM(result, pos++, NEW_eServiceReference(*it));
	}
	return result;
}

int eListboxServiceContent::getNextBeginningWithChar(char c)
{
//	printf("Char: %c\n", c);
	int index=0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i, ++index)
	{
		std::string text;
		ePtr<iStaticServiceInformation> service_info;
		if (m_service_center->info(*i, service_info))
		{
			continue; // failed to find service handler
		}
		service_info->getName(*i, text);
//		printf("%c\n", text.c_str()[0]);
		int idx=0;
		int len=text.length();
		while ( idx <= len )
		{
			char cc = text[idx++];
			if (isprint(cc))
			{
				if (cc == c)
					return index;
				break;
			}
		}
	}
	return 0;
}

int eListboxServiceContent::getPrevMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;

	// if the search is starting part way through a section return to the start of the current section
	while (index)
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	// if the search started from part way through the current section return now because this is the previous visible marker
	if (cursorResolve(index) + 1 != cursorResolve(m_cursor_number)) return cursorResolve(index);

	// search for visible marker index of previous section
	while (index)
	{
		--i;
		--index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}

	return cursorResolve(index);
}

int eListboxServiceContent::getNextMarkerPos()
{
	if (!m_listbox)
		return 0;
	list::iterator i(m_cursor);
	int index = m_cursor_number;
	while (index < (m_size-1))
	{
		++i;
		++index;
		if (i->flags == eServiceReference::isMarker)
			break;
	}
	return cursorResolve(index);
}

void eListboxServiceContent::initMarked()
{
	m_marked.clear();
}

void eListboxServiceContent::addMarked(const eServiceReference &ref)
{
	m_marked.insert(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

void eListboxServiceContent::removeMarked(const eServiceReference &ref)
{
	m_marked.erase(ref);
	if (m_listbox)
		m_listbox->entryChanged(cursorResolve(lookupService(ref)));
}

int eListboxServiceContent::isMarked(const eServiceReference &ref)
{
	return m_marked.find(ref) != m_marked.end();
}

void eListboxServiceContent::markedQueryStart()
{
	m_marked_iterator = m_marked.begin();
}

int eListboxServiceContent::markedQueryNext(eServiceReference &ref)
{
	if (m_marked_iterator == m_marked.end())
		return -1;
	ref = *m_marked_iterator++;
	return 0;
}

int eListboxServiceContent::lookupService(const eServiceReference &ref)
{
		/* shortcut for cursor */
	if (ref == *m_cursor)
		return m_cursor_number;
		/* otherwise, search in the list.. */
	int index = 0;
	for (list::const_iterator i(m_list.begin()); i != m_list.end(); ++i, ++index);

		/* this is ok even when the index was not found. */
	return index;
}

void eListboxServiceContent::setVisualMode(int mode)
{
	for (int i=0; i < celElements; ++i)
	{
		m_element_position[i] = eRect();
		m_element_font[i] = 0;
	}

	m_visual_mode = mode;

	if (m_visual_mode == visModeSimple)
	{
		m_element_position[celServiceName] = eRect(ePoint(0, 0), m_itemsize);
		m_element_font[celServiceName] = new gFont("Regular", 23);
	}
}

void eListboxServiceContent::setElementPosition(int element, eRect where)
{
	if ((element >= 0) && (element < celElements))
		m_element_position[element] = where;
}

void eListboxServiceContent::setElementFont(int element, gFont *font)
{
	if ((element >= 0) && (element < celElements))
		m_element_font[element] = font;
}

void eListboxServiceContent::setPixmap(int type, ePtr<gPixmap> &pic)
{
	if ((type >=0) && (type < picElements))
		m_pixmaps[type] = pic;
}

void eListboxServiceContent::sort()
{
	if (!m_lst)
		m_service_center->list(m_root, m_lst);
	if (m_lst)
	{
		m_list.sort(iListableServiceCompare(m_lst));
			/* FIXME: is this really required or can we somehow keep the current entry? */
		cursorHome();
		if (m_listbox)
			m_listbox->entryReset();
	}
}

DEFINE_REF(eListboxServiceContent);

eListboxServiceContent::eListboxServiceContent()
	:m_visual_mode(visModeSimple),m_cursor_number(0), m_saved_cursor_number(0), m_saved_cursor_line(0), m_size(0), m_current_marked(false),
	m_itemheight(25), m_hide_number_marker(false), m_show_two_lines(false), m_progress_view_mode(0), m_progress_text_width(0),
	m_service_picon_downsize(0), m_service_picon_ratio(167),m_servicetype_icon_mode(0), m_crypto_icon_mode(0),
	m_record_indicator_mode(0), m_column_width(0), m_progressbar_height(6), m_progressbar_border_width(2),
	m_nonplayable_margins(10), m_items_distances(8), m_progress_unit("%"), m_quality_icon_mode(0)   //// OPENSPA [morser] Add m_quality_icon_mode(0) for show service quality picons
{
	memset(m_color_set, 0, sizeof(m_color_set));
	m_numbering_mode = eSimpleConfig::getInt("config.usage.numberMode", 0);
	cursorHome();
	eServiceCenter::getInstance(m_service_center);
}

void eListboxServiceContent::setColor(int color, gRGB &col)
{
	if ((color >= 0) && (color < colorElements))
	{
		m_color_set[color] = true;
		m_color[color] = col;
	}
}

void eListboxServiceContent::swapServices(list::iterator a, list::iterator b)
{
	std::iter_swap(a, b);
	if(m_numbering_mode != 2)
	{
		int temp = a->getChannelNum();
		a->setChannelNum(b->getChannelNum());
		b->setChannelNum(temp);
	}
}

void eListboxServiceContent::cursorHome()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		if (m_cursor_number >= m_size)
		{
			m_cursor_number = m_size-1;
			--m_cursor;
		}
		while (m_cursor_number)
		{
			swapServices(m_cursor--, m_cursor);
			--m_cursor_number;
			if (m_listbox && m_cursor_number)
				m_listbox->entryChanged(cursorResolve(m_cursor_number));
		}
	}
	else
	{
		m_cursor = m_list.begin();
		m_cursor_number = 0;
		while (m_cursor != m_list.end())
		{
			if (!((m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) || (m_cursor->flags & eServiceReference::isInvisible)))
				break;
			m_cursor++;
			m_cursor_number++;
		}
	}
}

void eListboxServiceContent::cursorEnd()
{
	if (m_current_marked && m_saved_cursor == m_list.end())
	{
		while (m_cursor != m_list.end())
		{
			list::iterator prev = m_cursor++;
			++m_cursor_number;
			if ( prev != m_list.end() && m_cursor != m_list.end() )
			{
				swapServices(m_cursor, prev);
				if ( m_listbox )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
		}
	}
	else
	{
		m_cursor = m_list.end();
		m_cursor_number = m_size;
	}
}

int eListboxServiceContent::setCurrentMarked(bool state)
{
	bool prev = m_current_marked;
	m_current_marked = state;

	if (state != prev && m_listbox)
	{
		m_listbox->entryChanged(cursorResolve(m_cursor_number));
		if (!state)
		{
			if (!m_lst)
				m_service_center->list(m_root, m_lst);
			if (m_lst)
			{
				ePtr<iMutableServiceList> list;
				if (m_lst->startEdit(list))
					eDebug("[eListboxServiceContent] no editable list");
				else
				{
					eServiceReference ref;
					getCurrent(ref);
					if(!ref)
						eDebug("[eListboxServiceContent] no valid service selected");
					else
					{
						int pos = cursorGet();
						eDebugNoNewLineStart("[eListboxServiceContent] move %s to %d ", ref.toString().c_str(), pos);
						if (list->moveService(ref, cursorGet()))
							eDebugNoNewLine("failed\n");
						else
							eDebugNoNewLine("ok\n");
					}
				}
			}
			else
				eDebug("[eListboxServiceContent] no list available!");
		}
	}

	return 0;
}

int eListboxServiceContent::cursorMove(int count)
{
	int prev = m_cursor_number, last = m_cursor_number + count;
	if (count > 0)
	{
		while(count && m_cursor != m_list.end())
		{
			list::iterator prev_it = m_cursor++;
			if ( m_current_marked && m_cursor != m_list.end() && m_saved_cursor == m_list.end() )
			{
				swapServices(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
			++m_cursor_number;
			if (!(m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) && !(m_cursor->flags & eServiceReference::isInvisible))
				--count;
		}
	}
	else if (count < 0)
	{
		while (count && m_cursor != m_list.begin())
		{
			list::iterator prev_it = m_cursor--;
			if ( m_current_marked && m_cursor != m_list.end() && prev_it != m_list.end() && m_saved_cursor == m_list.end() )
			{
				swapServices(prev_it, m_cursor);
				if ( m_listbox && prev != m_cursor_number && last != m_cursor_number )
					m_listbox->entryChanged(cursorResolve(m_cursor_number));
			}
			--m_cursor_number;
			if (!(m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) && !(m_cursor->flags & eServiceReference::isInvisible))
				++count;
		}
		while (m_cursor != m_list.end())
		{
			if (!((m_marked.empty() && m_hide_number_marker && (m_cursor->flags & eServiceReference::isNumberedMarker)) || (m_cursor->flags & eServiceReference::isInvisible)))
				break;
			m_cursor++;
			m_cursor_number++;
		}
	}
	return 0;
}

int eListboxServiceContent::cursorValid()
{
	return m_cursor != m_list.end();
}

int eListboxServiceContent::cursorSet(int n)
{
	cursorHome();
	cursorMove(n);
	return 0;
}

int eListboxServiceContent::cursorResolve(int cursor_position)
{
	int m_stripped_cursor = 0;
	int count = 0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i)
	{
		if (count == cursor_position)
			break;

		count++;

		if ((m_marked.empty() && m_hide_number_marker && (i->flags & eServiceReference::isNumberedMarker)) || (i->flags & eServiceReference::isInvisible))
			continue;
		m_stripped_cursor++;
	}

	return m_stripped_cursor;
}

int eListboxServiceContent::cursorGet()
{
	return cursorResolve(m_cursor_number);
}

int eListboxServiceContent::currentCursorSelectable()
{
	if (cursorValid())
	{
		/* don't allow markers to be selected, unless we're in edit mode (because we want to provide some method to the user to remove a marker) */
		if ((m_cursor->flags & eServiceReference::isMarker) && m_marked.empty())
			return 0;
		else
			return 1;
	}
	return 0;
}

void eListboxServiceContent::cursorSave()
{
	m_saved_cursor = m_cursor;
	m_saved_cursor_number = m_cursor_number;
}

void eListboxServiceContent::cursorRestore()
{
	m_cursor = m_saved_cursor;
	m_cursor_number = m_saved_cursor_number;
	m_saved_cursor = m_list.end();
}

void eListboxServiceContent::cursorSaveLine(int line)
{
	m_saved_cursor_line = line;
}

int eListboxServiceContent::cursorRestoreLine()
{
	return m_saved_cursor_line;
}

int eListboxServiceContent::size()
{
	int size = 0;
	for (list::iterator i(m_list.begin()); i != m_list.end(); ++i)
	{
		if ((m_marked.empty() && m_hide_number_marker && (i->flags & eServiceReference::isNumberedMarker)) || (i->flags & eServiceReference::isInvisible))
			continue;
		size++;
	}

	return size;
}

void eListboxServiceContent::setSize(const eSize &size)
{
	m_itemsize = size;
	if (m_visual_mode == visModeSimple)
		setVisualMode(m_visual_mode);
}

void eListboxServiceContent::setGetPiconNameFunc(ePyObject func)
{
	if (m_GetPiconNameFunc)
		Py_DECREF(m_GetPiconNameFunc);
	m_GetPiconNameFunc = func;
	if (m_GetPiconNameFunc)
		Py_INCREF(m_GetPiconNameFunc);
}

void eListboxServiceContent::setIgnoreService( const eServiceReference &service )
{
	m_is_playable_ignore=service;
	if (m_listbox && m_listbox->isVisible())
		m_listbox->invalidate();
}

void eListboxServiceContent::setItemHeight(int height)
{
	m_itemheight = height;
	if (m_listbox)
		m_listbox->setItemHeight(height);
}

inline bool compareServices(const eServiceReference &src, const eServiceReference &trg) {
	return (src.toString() == trg.alternativeurl);
}

bool eListboxServiceContent::checkServiceIsRecorded(eServiceReference ref,pNavigation::RecordType type)
{
	std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > recordedServices;
	recordedServices = eNavigation::getInstance()->getRecordingsServices(type);
	for (std::map<ePtr<iRecordableService>, eServiceReference >::iterator it = recordedServices.begin(); it != recordedServices.end(); ++it)
	{
		if (ref.flags & eServiceReference::isGroup)
		{
			ePtr<iDVBChannelList> db;
			ePtr<eDVBResourceManager> res;
			eDVBResourceManager::getInstance(res);
			res->getChannelList(db);
			eBouquet *bouquet=0;
			db->getBouquet(ref, bouquet);
			for (std::list<eServiceReference>::iterator i(bouquet->m_services.begin()); i != bouquet->m_services.end(); ++i)
				if (*i == it->second || compareServices(*i, it->second))
					return true;
		}
		else if (ref == it->second || compareServices(ref, it->second))
			return true;
	}
	return false;
}

void eListboxServiceContent::paint(gPainter &painter, eWindowStyle &style, const ePoint &offset, int selected)
{
	painter.clip(eRect(offset, m_itemsize));

	int marked = 0;

	if (m_current_marked && selected)
		marked = 2;
	else if (cursorValid() && isMarked(*m_cursor))
	{
		if (selected)
			marked = 2;
		else
			marked = 1;
	}
	else
		style.setStyle(painter, selected ? eWindowStyle::styleListboxSelected : eWindowStyle::styleListboxNormal);

	eListboxStyle *local_style = 0;

		/* get local listbox style, if present */
	if (m_listbox)
		local_style = m_listbox->getLocalStyle();

	if (marked == 1)  // marked
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarked);
		if (m_color_set[markedForeground])
			painter.setForegroundColor(m_color[markedForeground]);
		if (m_color_set[markedBackground])
			painter.setBackgroundColor(m_color[markedBackground]);
	}
	else if (marked == 2) // marked and selected
	{
		style.setStyle(painter, eWindowStyle::styleListboxMarkedAndSelected);
		if (m_color_set[markedForegroundSelected])
			painter.setForegroundColor(m_color[markedForegroundSelected]);
		if (m_color_set[markedBackgroundSelected])
			painter.setBackgroundColor(m_color[markedBackgroundSelected]);
	}
	else if (local_style)
	{
		if (selected)
		{
			/* if we have a local background color set, use that. */
			if (local_style->is_set.background_color_selected)
				painter.setBackgroundColor(local_style->m_background_color_selected);
			/* same for foreground */
			if (local_style->is_set.foreground_color_selected)
				painter.setForegroundColor(local_style->m_foreground_color_selected);
		}
		else
		{
			/* if we have a local background color set, use that. */
			if (local_style->is_set.background_color)
				painter.setBackgroundColor(local_style->m_background_color);

			/* use alternative background color */
			if(local_style->is_set.background_color_rows)
			{
				if(cursorValid() && (cursorGet() % 2) == 0)
					painter.setBackgroundColor(local_style->m_background_color_rows);
			}

			/* same for foreground */
			if (local_style->is_set.foreground_color)
				painter.setForegroundColor(local_style->m_foreground_color);
		}
	}

	if (!local_style || !local_style->is_set.transparent_background)
		/* if we have no transparent background */
	{
		/* blit background picture, if available (otherwise, clear only) */
		if (local_style && local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), 0);
		else
			painter.clear();
	} else
	{
		if (local_style->m_background)
			painter.blit(local_style->m_background, offset, eRect(), gPainter::BT_ALPHABLEND);
		else if (selected && !local_style->m_selection)
			painter.clear();
	}

	if (cursorValid())
	{
		/* get service information */
		ePtr<iStaticServiceInformation> service_info;
		m_service_center->info(*m_cursor, service_info);
		eServiceReference ref = *m_cursor;
		bool isMarker = ref.flags & eServiceReference::isMarker;
		bool isPlayable = !(ref.flags & eServiceReference::isDirectory || isMarker);
		bool isRecorded = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref,pNavigation::RecordType(pNavigation::isRealRecording|pNavigation::isUnknownRecording));
		bool isStreamed = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref,pNavigation::isStreaming);
		bool isPseudoRecorded = m_record_indicator_mode && isPlayable && checkServiceIsRecorded(ref,pNavigation::isPseudoRecording);
		ePtr<eServiceEvent> evt;
		bool serviceAvail = true;
		bool serviceFallback = false;
		int isplayable_value;

		if (!marked && isPlayable && service_info && m_is_playable_ignore.valid())
		{
			isplayable_value = service_info->isPlayable(*m_cursor, m_is_playable_ignore);

			if (isplayable_value == 0) // service unavailable
			{
				if (m_color_set[serviceNotAvail])
					painter.setForegroundColor(m_color[serviceNotAvail]);
				else
					painter.setForegroundColor(gRGB(0xbbbbbb));
				serviceAvail = false;
			}
			else
			{
				if (isplayable_value == 2) // fallback receiver service
				{
					if (m_color_set[serviceItemFallback])
						painter.setForegroundColor(m_color[serviceItemFallback]);
					serviceFallback = true;
				}
			}
		}
		if (m_record_indicator_mode == 3 && isPseudoRecorded)
		{
			if (m_color_set[servicePseudoRecorded])
				painter.setForegroundColor(m_color[servicePseudoRecorded]);
			else
				painter.setForegroundColor(gRGB(0x41b1ec));
		}
		if (m_record_indicator_mode == 3 && isStreamed)
		{
			if (m_color_set[serviceStreamed])
				painter.setForegroundColor(m_color[serviceStreamed]);
			else
				painter.setForegroundColor(gRGB(0xf56712));
		}
		if (m_record_indicator_mode == 3 && isRecorded)
		{
			if (m_color_set[serviceRecordingColor])
				painter.setForegroundColor(m_color[serviceRecordingColor]);
			else if (m_color_set[serviceRecorded])
				painter.setForegroundColor(m_color[serviceRecorded]);
			else
				painter.setForegroundColor(gRGB(0xb40431));
		}

		if (selected && local_style && local_style->m_selection)
			painter.blit(local_style->m_selection, offset, eRect(), gPainter::BT_ALPHABLEND);

		int xoffset=0;  // used as offset when painting the folder/marker symbol or the serviceevent progress
		int nameLeft=0, nameWidth=0, nameYoffs=0, serviceTypeXoffs=0; // used as temporary values for 'show two lines' option

		time_t now = time(0);

		for (int e = 0; e != celServiceTypePixmap; ++e)
		{
			if (m_element_font[e])
			{
				int flags=gPainter::RT_VALIGN_CENTER;
				int yoffs = 0;
				eRect area = m_element_position[e];
				std::string text = "<n/a>";
				switch (e)
				{
				case celServiceNumber:
				{
					if (area.width() <= 0)
						continue; // no point in going on if we won't paint anything

					if( m_cursor->getChannelNum() == 0 )
						continue;

					char buffer[15];
					snprintf(buffer, sizeof(buffer), "%d", m_cursor->getChannelNum() );
					text = buffer;
					flags|=gPainter::RT_HALIGN_RIGHT;
					if (isPlayable && serviceFallback && selected && m_color_set[serviceSelectedFallback])
						painter.setForegroundColor(m_color[serviceSelectedFallback]);
					break;
				}
				case celServiceName:
				{
					if (service_info)
						service_info->getName(*m_cursor, text);
#ifdef USE_LIBVUGLES2
					painter.setFlush(text == "<n/a>");
#endif
					if (!isPlayable)
					{
						area.setWidth(area.width() + m_element_position[celServiceEventProgressbar].width() +  m_nonplayable_margins);
						if (m_element_position[celServiceEventProgressbar].left() == m_element_position[celServiceNumber].left())
							area.setLeft(m_element_position[celServiceNumber].left());
						if (m_element_position[celServiceNumber].width() && m_element_position[celServiceEventProgressbar].left() == m_element_position[celServiceNumber].width() +  m_nonplayable_margins)
							area.setLeft(m_element_position[celServiceNumber].width() +  m_nonplayable_margins);
					}
					if (!(m_record_indicator_mode == 3 && isRecorded) && isPlayable && serviceFallback && selected && m_color_set[serviceSelectedFallback])
						painter.setForegroundColor(m_color[serviceSelectedFallback]);
					break;
				}
				case celServiceInfo:
				{
					if ( isPlayable && service_info && !service_info->getEvent(*m_cursor, evt) )
					{
						std::string name = evt->getEventName();
						if (name.empty())
							continue;
						text = evt->getEventName();
						if (serviceAvail)
						{
							if (!selected)
							{
								if (serviceFallback && m_color_set[eventForegroundFallback]) // fallback receiver
									painter.setForegroundColor(m_color[eventForegroundFallback]);
								else if(m_color_set[serviceDescriptionColor])
									painter.setForegroundColor(m_color[serviceDescriptionColor]);
								else if(m_color_set[eventForeground]) //serviceDescriptionColor
									painter.setForegroundColor(m_color[eventForeground]);
								else	//default color (Tulip Tree)
									painter.setForegroundColor(gRGB(0xe7b53f));

							}
							else
							{
								if (serviceFallback && m_color_set[eventForegroundSelectedFallback])
									painter.setForegroundColor(m_color[eventForegroundSelectedFallback]);
								else if(m_color_set[serviceDescriptionColorSelected])
									painter.setForegroundColor(m_color[serviceDescriptionColorSelected]);
								else if(m_color_set[eventForeground]) //serviceDescriptionColor
									painter.setForegroundColor(m_color[eventForegroundSelected]);
								else	//default color (Tulip Tree)
									painter.setForegroundColor(gRGB(0xe7b53f));

							}
						}
						break;
					}
					continue;
				}
				case celServiceEventProgressbar:
				{
					if (area.width() > 0 && isPlayable && service_info && !service_info->getEvent(*m_cursor, evt))
					{
						char buffer[15];
						if (m_progress_unit == "%")
							snprintf(buffer, sizeof(buffer), "%d %%", (int)(100 * (now - evt->getBeginTime()) / evt->getDuration()));
						else
							snprintf(buffer, sizeof(buffer), "+%d %s", (int)((evt->getBeginTime() + evt->getDuration() - now)/60), m_progress_unit.c_str());
						text = buffer;
						flags|=gPainter::RT_HALIGN_RIGHT;
						break;
					}
					continue;
				}
				}

				eRect tmp = area;
				int xoffs = 0;
				ePtr<gPixmap> piconPixmap;

				if (e == celServiceName)
				{
					// openspa [morser] Show picon for bouquets
					//picon stuff
					if ((isPlayable || eServiceReference::isGroup ) && PyCallable_Check(m_GetPiconNameFunc))
					{
						ePyObject pArgs = PyTuple_New(1);
						PyTuple_SET_ITEM(pArgs, 0, PyUnicode_FromString(ref.toString().c_str()));
						ePyObject pRet = PyObject_CallObject(m_GetPiconNameFunc, pArgs);
						Py_DECREF(pArgs);
						if (pRet)
						{
							if (PyUnicode_Check(pRet))
							{
								std::string piconFilename = PyUnicode_AsUTF8(pRet);
								if (!piconFilename.empty())
									loadPNG(piconPixmap, piconFilename.c_str());
							}
							Py_DECREF(pRet);
						}
					}
					xoffs = xoffset;
					tmp.setWidth(((!isPlayable || m_column_width == -1 || (!piconPixmap && !m_column_width)) ? tmp.width() : m_column_width) - xoffs);
				}

				ePtr<eTextPara> para = new eTextPara(tmp);
				para->setFont(m_element_font[e]);
				para->renderString(text.c_str());

				if (e == celServiceName)
				{
					eRect bbox = para->getBoundBox();

					int servicenameWidth = ((!isPlayable || m_column_width == -1 || (!piconPixmap && !m_column_width)) ? bbox.width() : m_column_width);
					m_element_position[celServiceInfo].setLeft(area.left() + servicenameWidth + m_items_distances + xoffs);
					m_element_position[celServiceInfo].setTop(area.top());
					m_element_position[celServiceInfo].setWidth(area.width() - (servicenameWidth + m_items_distances + xoffs));
					m_element_position[celServiceInfo].setHeight(area.height());
					nameLeft = area.left();
					nameWidth = area.width();

					// openspa [morser] show picon for bouquets
					if (isPlayable || (eServiceReference::isGroup && eConfigManager::getConfigBoolValue("config.usage.bouquet_icon_enable", false)))
					{
						//picon stuff
						if (PyCallable_Check(m_GetPiconNameFunc) and (m_column_width || piconPixmap))
						{
							eRect area = m_element_position[celServiceInfo];
							/* Picons are usually about 100:60. Make it a
							 * bit wider in case the icons are diffently
							 * shaped, and to add a bit of margin between
							 * icon and text. */
							const int iconWidth = (area.height() + m_service_picon_downsize * 2) * (m_service_picon_ratio * 0.01);
							m_element_position[celServiceInfo].setLeft(area.left() + iconWidth + m_items_distances);
							m_element_position[celServiceInfo].setWidth(area.width() - iconWidth - m_items_distances);
							area = m_element_position[celServiceName];
							xoffs += iconWidth + m_items_distances;
							if (piconPixmap)
							{
								// openspa [morser] show picon for bouquets
								int picon_offset = 0;
								if (!isPlayable && eServiceReference::isGroup)
								{
									picon_offset = m_pixmaps[picServiceGroup]->size().width() + m_items_distances;
								}
								///////////////
								area.moveBy(offset);
								painter.clip(area);
								painter.blitScale(piconPixmap,
									eRect(area.left() + picon_offset , area.top() - m_service_picon_downsize, iconWidth, area.height() + m_service_picon_downsize * 2),
									area,
									gPainter::BT_ALPHABLEND | gPainter::BT_KEEP_ASPECT_RATIO | gPainter::BT_HALIGN_CENTER | gPainter::BT_VALIGN_CENTER);  // openspa [morser] show picon for bouquets
								painter.clippop();
							}
						}
					}

					if (isPlayable)
					{
						//record icon stuff part1
						int rec_pixmap_xoffs = 0;
						if (isRecorded && m_record_indicator_mode == 1 && m_pixmaps[picRecord])
							rec_pixmap_xoffs = m_pixmaps[picRecord]->size().width() + m_items_distances;

						//service type marker stuff
						if (m_servicetype_icon_mode)
						{
							int orbpos = m_cursor->getUnsignedData(4) >> 16;
							const char *filename = ref.path.c_str();
							ePtr<gPixmap> &pixmap =
								(m_cursor->flags & eServiceReference::isGroup) ? m_pixmaps[picServiceGroup] :
								(strstr(filename, "://")) ? m_pixmaps[picStream] :
								(orbpos == 0xFFFF) ? m_pixmaps[picDVB_C] :
								(orbpos == 0xEEEE) ? m_pixmaps[picDVB_T] : m_pixmaps[picDVB_S];
							if (pixmap)
							{
								eSize pixmap_size = pixmap->size();
								eRect area = m_element_position[celServiceInfo];
								m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
								int offs = rec_pixmap_xoffs;
								if (m_servicetype_icon_mode == 1)
								{
									area = m_element_position[celServiceName];
									offs = xoffs;
									serviceTypeXoffs = offs;
									xoffs += pixmap_size.width() + m_items_distances;
								}
								else if (m_crypto_icon_mode == 1 && m_pixmaps[picCrypto])
									offs = offs + m_pixmaps[picCrypto]->size().width() + m_items_distances;
								int correction = (m_show_two_lines) ? (((area.height()/2) - pixmap_size.height()) / 2) + 2 : (area.height() - pixmap_size.height()) / 2;
								area.moveBy(offset);
								painter.clip(area);
								painter.blit(pixmap, ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
								painter.clippop();
							}
						}

						////////////// OPENSPA [morser] Show service quality picons ////////////////
						//service quality stuff
						if (m_quality_icon_mode)
						{
							if (service_info)
								service_info->getName(*m_cursor, text);
							bool is3D = (eDVBDB::getInstance()->HasFlag(ref, 128) | text.find("3D") != std::string::npos) ? true: false;
							bool isHD = false;
							bool isUHD = false;
							bool isIPTV = false;
							const char *url = ref.path.c_str();

							if (strstr(url, "://") && eConfigManager::getConfigBoolValue("config.usage.quality_IPTVicon", true))
							{
								isIPTV = true;
							} else {
								isHD = ref.data[0] == 25 | text.find(" HD") != std::string::npos | text.find(" FHD") != std::string::npos;
								isUHD = ref.data[0] == 31 | text.find(" UHD") != std::string::npos | text.find(" 4K") != std::string::npos;
							}

							ePtr<gPixmap> &pixmap =
								(is3D & eConfigManager::getConfigBoolValue("config.usage.quality_3Dicon", true)) ? m_pixmaps[pic3D] :
								(isUHD & eConfigManager::getConfigBoolValue("config.usage.quality_4Kicon", true)) ? m_pixmaps[pic4K] :
								(isHD & eConfigManager::getConfigBoolValue("config.usage.quality_HDicon", true)) ? m_pixmaps[picHD] :
								(ref.data[0] == 1 & eConfigManager::getConfigBoolValue("config.usage.quality_SDicon", false)) ? m_pixmaps[picSD]:
								isIPTV ? m_pixmaps[picIPTV] : m_pixmaps[picNone];

							eSize pixmap_size = m_pixmaps[picHD]->size();

							eRect area = m_element_position[celServiceInfo];
							int offs = 0;
							if (m_quality_icon_mode == 1)
							{
								m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
								area = m_element_position[celServiceName];
								offs = xoffs;
								xoffs += pixmap_size.width() + m_items_distances;
							}
							int correction = (area.height() - pixmap_size.height()) / 2;
							area.moveBy(offset);
							if (pixmap)
							{
								if (m_quality_icon_mode == 2)
								{
									m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
									m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
									if (m_crypto_icon_mode == 1 && m_pixmaps[picCrypto])
										offs = offs + m_pixmaps[picCrypto]->size().width() + m_items_distances;
								}
								painter.clip(area);
								painter.blit(pixmap, ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
								painter.clippop();
 							}
 						}
						////////////////////////////////////////////////////////////////////////////////

						//crypto icon stuff
						if (m_crypto_icon_mode && m_pixmaps[picCrypto])
						{
							eSize pixmap_size = m_pixmaps[picCrypto]->size();
							eRect area = m_element_position[celServiceInfo];
							int offs = rec_pixmap_xoffs;
							if (m_crypto_icon_mode == 1)
							{
								m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
								area = m_element_position[celServiceName];
								offs = xoffs;
								xoffs += pixmap_size.width() + m_items_distances;
							}
							int correction = (m_show_two_lines) ? (((area.height()/2) - pixmap_size.height()) / 2) + 2 : (area.height() - pixmap_size.height()) / 2;
							if (m_show_two_lines && m_servicetype_icon_mode == 1 && m_crypto_icon_mode == 1)
							{
								correction = (((area.height()/2) - pixmap_size.height()) + area.height()) / 2 + 2;
								xoffs -= pixmap_size.width() + m_items_distances;
								offs = serviceTypeXoffs + (xoffs - serviceTypeXoffs - pixmap_size.width() - m_items_distances) / 2;
								serviceTypeXoffs = pixmap_size.width() + m_items_distances;
							}
							area.moveBy(offset);
							//OPENSPA [morser] prepare for IPTV crypted pic
							const char *uri = ref.path.c_str();
							bool isIPTVCrypted = (strstr(uri, "://") && ref.flags == eServiceReference::isIPTVCrypted); //OPENSPA [morser] prepare for IPTV crypted pic
							if (service_info && service_info->isCrypted() || isIPTVCrypted)   //OPENSPA [morser] prepare for IPTV crypted pic
							{
								if (m_crypto_icon_mode == 2)
								{
									m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
									m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
								}
								painter.clip(area);
								painter.blit(m_pixmaps[picCrypto], ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
								painter.clippop();
							}
						}

						//record icon stuff part2
						if (isRecorded && m_record_indicator_mode < 3 && m_pixmaps[picRecord])
						{
							eSize pixmap_size = m_pixmaps[picRecord]->size();
							eRect area = m_element_position[celServiceInfo];
							int offs = 0;
							if (m_record_indicator_mode == 1)
							{
								m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
								area = m_element_position[celServiceName];
								offs = xoffs;
								xoffs += pixmap_size.width() + m_items_distances;
							}
							int correction = (m_show_two_lines && m_record_indicator_mode == 2) ? (((area.height()/2) - pixmap_size.height()) / 2) + 2 : (area.height() - pixmap_size.height()) / 2;
							area.moveBy(offset);
							if (m_record_indicator_mode == 2)
							{
								m_element_position[celServiceInfo].setLeft(area.left() + pixmap_size.width() + m_items_distances);
								m_element_position[celServiceInfo].setWidth(area.width() - pixmap_size.width() - m_items_distances);
							}
							if (m_show_two_lines && m_servicetype_icon_mode == 1 && m_crypto_icon_mode == 1)
								area.setLeft(area.left() - serviceTypeXoffs);
							painter.clip(area);
							painter.blit(m_pixmaps[picRecord], ePoint(area.left() + offs, offset.y() + correction), area, gPainter::BT_ALPHABLEND);
							painter.clippop();
						}

						if (m_show_two_lines)
						{
							m_element_position[celServiceInfo].setLeft(nameLeft+xoffs);
							if (!m_progress_view_mode || m_progress_view_mode == 2 || m_element_position[celServiceEventProgressbar].left() <= m_element_position[celServiceName].right())
								m_element_position[celServiceInfo].setWidth(nameWidth - xoffs);
							else if (m_progress_view_mode == 1)
								m_element_position[celServiceInfo].setWidth(nameWidth - xoffs + m_element_position[celServiceEventProgressbar].width() - m_progress_text_width);
							else
								m_element_position[celServiceInfo].setWidth(nameWidth - xoffs + m_element_position[celServiceEventProgressbar].width() + m_items_distances);
						}
					}
				}

				if (flags & gPainter::RT_HALIGN_RIGHT)
					para->realign(eTextPara::dirRight);
				else if (flags & gPainter::RT_HALIGN_CENTER)
					para->realign(eTextPara::dirCenter);
				else if (flags & gPainter::RT_HALIGN_BLOCK)
					para->realign(eTextPara::dirBlock);

				if (flags & gPainter::RT_VALIGN_CENTER)
				{
					eRect bbox = para->getBoundBox();
					if (m_show_two_lines && e == celServiceName && isPlayable)
					{
						yoffs = ((area.height()/2) - bbox.height()) / 2 - bbox.top();
						nameYoffs = yoffs/2;
					}
					else if (m_show_two_lines && e == celServiceInfo)
						yoffs = (area.height() + ((area.height()/2) - bbox.height())) / 2 - (bbox.top() - nameYoffs);
					else if (m_show_two_lines && e == celServiceEventProgressbar && m_progress_view_mode == 1)
						yoffs = area.height() + (area.height() - bbox.height()) / 2 - bbox.top();
					else if (m_show_two_lines && e == celServiceEventProgressbar && m_progress_view_mode == 12)
					{
						yoffs = (area.height() - bbox.height()) / 2 - bbox.top();
						xoffs -= (m_element_position[celServiceEventProgressbar].width() - m_progress_text_width);
					}
					else
						yoffs = (area.height() - bbox.height()) / 2 - bbox.top();
				}

				painter.renderPara(para, offset+ePoint(xoffs, yoffs));
			}
			else if ((e == celFolderPixmap && m_cursor->flags & eServiceReference::isDirectory) ||
				(e == celMarkerPixmap && m_cursor->flags & eServiceReference::isMarker &&
				!(m_cursor->flags & eServiceReference::isNumberedMarker)))
			{
				ePtr<gPixmap> &pixmap =
					(e == celFolderPixmap) ? m_pixmaps[picFolder] : m_pixmaps[picMarker];
				if (pixmap)
				{
					eSize pixmap_size = pixmap->size();
					eRect area = m_element_position[e == celFolderPixmap ? celServiceName: celServiceNumber];
					if (m_show_two_lines)
						area.setHeight(m_itemsize.height());
					int correction = (m_itemsize.height() - pixmap_size.height()) / 2;
					if (e == celFolderPixmap && m_element_position[celServiceEventProgressbar].left() == m_element_position[celServiceNumber].left())
						area.setLeft(m_element_position[celServiceNumber].left());
					xoffset = pixmap_size.width() + m_items_distances;
					area.moveBy(offset);
					painter.clip(area);
					painter.blit(pixmap, ePoint(area.left(), offset.y() + correction), area, gPainter::BT_ALPHABLEND);
					painter.clippop();
				}
			}
		}
		if (selected && (!local_style || !local_style->m_selection))
			style.drawFrame(painter, eRect(offset, m_itemsize), eWindowStyle::frameListboxEntry);

		eRect area = m_element_position[celServiceEventProgressbar];
		if (area.width() > 0 && evt && (!m_element_font[celServiceEventProgressbar] || (m_show_two_lines && m_progress_view_mode%10)))
		{
			int correction = (m_show_two_lines && m_progress_view_mode == 2) ? area.height() : 0;
			int pb_xpos = (m_show_two_lines && m_progress_view_mode == 12) ? area.left() + m_progress_text_width + m_items_distances : area.left();
			int pb_ypos = offset.y() + correction + (area.height() - m_progressbar_height - 2 * m_progressbar_border_width) / 2;
			int pb_width = (m_show_two_lines && m_progress_view_mode > 10) ? area.width() - m_progress_text_width - m_items_distances - 2 * m_progressbar_border_width : area.width()- 2 * m_progressbar_border_width;
			gRGB ProgressbarBorderColor = 0xdfdfdf;
			int evt_done = pb_width * (now - evt->getBeginTime()) / evt->getDuration();

			// the progress data...
			eRect tmp = eRect(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width, evt_done, m_progressbar_height);
			ePtr<gPixmap> &pixmap = m_pixmaps[picServiceEventProgressbar];
			if (pixmap) {
				painter.clip(tmp);
				painter.blit(pixmap, ePoint(pb_xpos + m_progressbar_border_width, pb_ypos + m_progressbar_border_width), tmp, gPainter::BT_ALPHABLEND);
				painter.clippop();
			}
			else {
				if (!selected && m_color_set[serviceEventProgressbarColor])
					painter.setForegroundColor(m_color[serviceEventProgressbarColor]);
				else if (selected && m_color_set[serviceEventProgressbarColorSelected])
					painter.setForegroundColor(m_color[serviceEventProgressbarColorSelected]);
				painter.fill(tmp);
			}

			// the progressbar border
			if (!selected)  {
				if (m_color_set[serviceEventProgressbarBorderColor])
					ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColor];
				else if (m_color_set[eventborderForeground])
					ProgressbarBorderColor = m_color[eventborderForeground];
			}
			else { /* !selected */
				if (m_color_set[serviceEventProgressbarBorderColorSelected])
					ProgressbarBorderColor = m_color[serviceEventProgressbarBorderColorSelected];
				else if (m_color_set[eventborderForegroundSelected])
					ProgressbarBorderColor = m_color[eventborderForegroundSelected];
			}
			painter.setForegroundColor(ProgressbarBorderColor);

			if (m_progressbar_border_width)
			{
				painter.fill(eRect(pb_xpos, pb_ypos, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
				painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width + m_progressbar_height, pb_width + 2 * m_progressbar_border_width,  m_progressbar_border_width));
				painter.fill(eRect(pb_xpos, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
				painter.fill(eRect(pb_xpos + m_progressbar_border_width + pb_width, pb_ypos + m_progressbar_border_width, m_progressbar_border_width, m_progressbar_height));
			}
			else
				painter.fill(eRect(pb_xpos + evt_done, pb_ypos, pb_width - evt_done,  m_progressbar_height));
		}
	}
	painter.clippop();
}
